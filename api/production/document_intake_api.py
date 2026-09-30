from __future__ import annotations

from datetime import date
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from .auth import audit, require_permission
from .document_ai_provider import extract_invoice

router = APIRouter(prefix="/api/documents/intake", tags=["document-intake"])

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_FILE_BYTES = int(os.getenv("DOCUMENT_INTAKE_MAX_BYTES", str(15 * 1024 * 1024)))


def db():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


def storage_root() -> Path:
    root = Path(os.getenv("DOCUMENT_INTAKE_DIR", "/var/lib/eyt-erp/documents"))
    root.mkdir(parents=True, exist_ok=True)
    return root


class ExtractionLine(BaseModel):
    lineNo: int = Field(gt=0)
    rawDescription: str | None = None
    productCode: str | None = Field(default=None, max_length=100)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=30)
    unitPrice: Decimal | None = Field(default=None, ge=0)
    discountAmount: Decimal = Field(default=Decimal("0"), ge=0)
    taxAmount: Decimal = Field(default=Decimal("0"), ge=0)
    lineTotal: Decimal | None = None
    matchConfidence: Decimal | None = Field(default=None, ge=0, le=1)
    extractedData: dict = Field(default_factory=dict)


class ExtractionPayload(BaseModel):
    documentType: str = Field(min_length=1, max_length=40)
    supplierCode: str | None = Field(default=None, max_length=60)
    invoiceNo: str | None = Field(default=None, max_length=100)
    invoiceDate: date | None = None
    dueDate: date | None = None
    currency: str = Field(default="IRR", max_length=10)
    subtotal: Decimal | None = None
    discountAmount: Decimal | None = None
    taxAmount: Decimal | None = None
    totalAmount: Decimal | None = None
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    extractedData: dict = Field(default_factory=dict)


class ValidationResult(BaseModel):
    valid: bool
    errors: list[dict] = Field(default_factory=list)


def _event(conn, document_id: UUID, event_type: str, actor_id, details: dict):
    conn.execute(
        """INSERT INTO document_intake_events(document_id,event_type,actor_user_id,details)
           VALUES(%s,%s,%s,%s)""",
        (document_id, event_type, actor_id, json.dumps(details)),
    )


def _validate_extraction(conn, payload: ExtractionPayload) -> list[dict]:
    errors: list[dict] = []

    if payload.documentType == "PURCHASE_INVOICE":
        if not payload.supplierCode:
            errors.append({"code": "SUPPLIER_REQUIRED", "message": "supplierCode is required"})
        elif not conn.execute(
            "SELECT 1 FROM eyt_suppliers WHERE supplier_code=%s AND status='active'",
            (payload.supplierCode,),
        ).fetchone():
            errors.append({"code": "SUPPLIER_UNKNOWN", "message": "Supplier is not known or active"})

        if not payload.invoiceNo:
            errors.append({"code": "INVOICE_NO_REQUIRED", "message": "invoiceNo is required"})

        if payload.totalAmount is None:
            errors.append({"code": "TOTAL_REQUIRED", "message": "totalAmount is required"})

        seen = set()
        calculated = Decimal("0")
        for line in payload.lines:
            if line.lineNo in seen:
                errors.append({"code": "DUPLICATE_LINE_NO", "message": f"Duplicate lineNo: {line.lineNo}"})
            seen.add(line.lineNo)
            if line.productCode and not conn.execute("SELECT 1 FROM products WHERE product_code=%s AND is_active", (line.productCode,)).fetchone():
                errors.append({"code": "UNKNOWN_PRODUCT", "message": f"Unknown productCode: {line.productCode}", "lineNo": line.lineNo})
            if line.lineTotal is not None:
                calculated += line.lineTotal
        if payload.totalAmount is not None and payload.lines and abs(calculated - payload.totalAmount) > Decimal("0.01"):
            errors.append({"code": "ARITHMETIC_MISMATCH", "message": "Invoice line totals do not reconcile to document total"})
        
        if payload.invoiceNo and payload.supplierCode:
            duplicate = conn.execute(
                """SELECT id FROM document_intake_items
                   WHERE supplier_code=%s AND invoice_no=%s
                     AND status NOT IN ('FAILED','BLOCKED')""",
                (payload.supplierCode, payload.invoiceNo),
            ).fetchone()
            if duplicate:
                errors.append({"code": "DUPLICATE_INVOICE", "message": "Invoice already exists in intake"})

    return errors


@router.post("", status_code=201)
async def intake_document(
    request: Request,
    file: UploadFile = File(...),
    principal: dict = Depends(require_permission("document.intake")),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Only PDF/JPEG/PNG/WEBP documents are accepted")

    document_id = uuid4()
    target_dir = storage_root() / str(document_id)
    target_dir.mkdir(parents=True, exist_ok=False)
    target = target_dir / Path(file.filename or "document").name

    size = 0
    digest = hashlib.sha256()
    try:
        with target.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(413, "Document is too large")
                digest.update(chunk)
                out.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        target_dir.rmdir()
        raise

    sha256 = digest.hexdigest()

    with db() as conn:
        existing = conn.execute(
            "SELECT id,status FROM document_intake_items WHERE sha256=%s",
            (sha256,),
        ).fetchone()
        if existing:
            target.unlink(missing_ok=True)
            target_dir.rmdir()
            return {
                "id": str(existing[0]),
                "status": existing[1],
                "duplicate": True,
            }

        conn.execute(
            """INSERT INTO document_intake_items
               (id,original_filename,content_type,storage_path,sha256,file_size_bytes,source_channel,created_by)
               VALUES(%s,%s,%s,%s,%s,%s,'UPLOAD',%s)""",
            (
                document_id,
                file.filename or "document",
                file.content_type,
                str(target),
                sha256,
                size,
                principal["id"],
            ),
        )
        _event(conn, document_id, "RECEIVED", principal["id"], {"filename": file.filename})
        conn.commit()

    audit(request, principal, "document.intake.received", document_id, {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": size,
        "sha256": sha256,
    })

    return {
        "id": str(document_id),
        "status": "RECEIVED",
        "next": "OCR_AI_EXTRACTION",
        "originalFilename": file.filename,
        "sha256": sha256,
    }


@router.post("/{document_id}/extract-ai")
def extract_ai(document_id: UUID, request: Request, principal: dict = Depends(require_permission("document.intake"))):
    with db() as conn:
        row = conn.execute("SELECT id,storage_path,status FROM document_intake_items WHERE id=%s FOR UPDATE", (document_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Document not found")
        if row[1] in ("POSTED",):
            raise HTTPException(409, "Document is already posted")
        conn.execute("UPDATE document_intake_items SET status=%s WHERE id=%s", ("EXTRACTING", document_id))
        conn.commit()
    try:
        extracted = extract_invoice(row[2])
    except Exception as exc:
        with db() as conn:
            conn.execute("UPDATE document_intake_items SET status=%s,validation_errors=%s WHERE id=%s", ("FAILED", json.dumps([{"code":"AI_EXTRACTION_FAILED","message":str(exc)[:500]}]), document_id))
            _event(conn, document_id, "AI_EXTRACTION_FAILED", principal["id"], {"error": str(exc)[:500]})
            conn.commit()
        raise HTTPException(502, "AI extraction failed") from exc
    payload = ExtractionPayload.model_validate(extracted)
    return submit_extraction(document_id, payload, request, principal)

@router.post("/{document_id}/extraction")
def submit_extraction(
    document_id: UUID,
    payload: ExtractionPayload,
    request: Request,
    principal: dict = Depends(require_permission("document.intake")),
):
    with db() as conn:
        row = conn.execute(
            "SELECT id,status FROM document_intake_items WHERE id=%s FOR UPDATE",
            (document_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Document not found")

        errors = _validate_extraction(conn, payload)
        status = "READY_TO_POST" if not errors else "REVIEW"

        conn.execute(
            """UPDATE document_intake_items
               SET document_type=%s,supplier_code=%s,invoice_no=%s,
                   invoice_date=%s,due_date=%s,currency=%s,
                   subtotal=%s,discount_amount=%s,tax_amount=%s,total_amount=%s,
                   extraction_confidence=%s,extracted_data=%s,validation_errors=%s,
                   status=%s,extracted_at=now()
               WHERE id=%s""",
            (
                payload.documentType, payload.supplierCode, payload.invoiceNo,
                payload.invoiceDate, payload.dueDate, payload.currency,
                payload.subtotal, payload.discountAmount, payload.taxAmount,
                payload.totalAmount, payload.confidence,
                json.dumps(payload.extractedData), json.dumps(errors),
                status, document_id,
            ),
        )
        conn.execute("DELETE FROM document_intake_line_items WHERE document_id=%s", (document_id,))
        for line in payload.lines:
            line_errors = [e for e in errors if e.get("lineNo") == line.lineNo]
            match_status = "MATCHED" if line.productCode and not line_errors else "REVIEW"
            conn.execute(
                """INSERT INTO document_intake_line_items
                   (document_id,line_no,raw_description,product_code,quantity,unit,unit_price,
                    discount_amount,tax_amount,line_total,match_status,match_confidence,extracted_data)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (document_id,line.lineNo,line.rawDescription,line.productCode,line.quantity,
                 line.unit,line.unitPrice,line.discountAmount,line.taxAmount,line.lineTotal,
                 match_status,line.matchConfidence,json.dumps(line.extractedData)),
            )
        calculated = sum((x.lineTotal or Decimal("0") for x in payload.lines), Decimal("0"))
        variance = (calculated - payload.totalAmount) if payload.totalAmount is not None and payload.lines else None
        conn.execute("UPDATE document_intake_items SET line_count=%s,calculated_lines_total=%s,arithmetic_variance=%s WHERE id=%s",
                     (len(payload.lines),calculated,variance,document_id))
        _event(conn, document_id, "EXTRACTED", principal["id"], {
            "status": status,
            "error_count": len(errors),
        })
        conn.commit()

    audit(request, principal, "document.intake.extracted", document_id, {
        "status": status,
        "error_count": len(errors),
    })

    return {
        "id": str(document_id),
        "status": status,
        "validation": {"valid": not errors, "errors": errors},
    }


@router.get("/{document_id}")
def get_document(
    document_id: UUID,
    _=Depends(require_permission("document.intake.read")),
):
    with db() as conn:
        row = conn.execute(
            """SELECT id,original_filename,content_type,storage_path,sha256,file_size_bytes,
                      source_channel,document_type,status,supplier_code,invoice_no,
                      invoice_date,due_date,currency,subtotal,discount_amount,tax_amount,
                      total_amount,extraction_confidence,extracted_data,validation_errors,
                      posted_reference_type,posted_reference_id,created_at,extracted_at,posted_at
               FROM document_intake_items WHERE id=%s""",
            (document_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")

    keys = [
        "id","originalFilename","contentType","storagePath","sha256","fileSizeBytes",
        "sourceChannel","documentType","status","supplierCode","invoiceNo",
        "invoiceDate","dueDate","currency","subtotal","discountAmount","taxAmount",
        "totalAmount","extractionConfidence","extractedData","validationErrors",
        "postedReferenceType","postedReferenceId","createdAt","extractedAt","postedAt",
    ]
    result = dict(zip(keys, row))
    result["id"] = str(result["id"])
    return result


@router.post("/{document_id}/validate")
def validate_document(
    document_id: UUID,
    request: Request,
    principal: dict = Depends(require_permission("document.intake")),
):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM document_intake_items WHERE id=%s FOR UPDATE",
            (document_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Document not found")

        # Re-run only deterministic business validation. OCR/AI never gets
        # permission to mutate ERP source-of-truth tables.
        payload = ExtractionPayload(
            documentType=row[7] or "UNKNOWN",
            supplierCode=row[8],
            invoiceNo=row[9],
            invoiceDate=row[10],
            dueDate=row[11],
            currency=row[12] or "IRR",
            subtotal=row[13],
            discountAmount=row[14],
            taxAmount=row[15],
            totalAmount=row[16],
            confidence=row[17],
            extractedData=row[18] or {},
        )
        errors = _validate_extraction(conn, payload)
        status = "READY_TO_POST" if not errors else "REVIEW"
        conn.execute(
            "UPDATE document_intake_items SET validation_errors=%s,status=%s WHERE id=%s",
            (json.dumps(errors), status, document_id),
        )
        _event(conn, document_id, "VALIDATED", principal["id"], {"status": status, "error_count": len(errors)})
        conn.commit()

    audit(request, principal, "document.intake.validated", document_id, {"status": status})
    return {"id": str(document_id), "status": status, "errors": errors}
