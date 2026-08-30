"""Operational QC, batch traceability and finished-goods release API."""
from decimal import Decimal
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_permission

router = APIRouter(prefix="/api/qc", tags=["quality-control"])


def _connect():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(database_url, row_factory=dict_row)


class BatchInput(BaseModel):
    batch_no: str = Field(min_length=1, max_length=100)
    production_order_no: str = Field(min_length=1, max_length=80)
    product_code: str = Field(min_length=1, max_length=100)
    planned_qty: Decimal = Field(gt=0)


class InspectionInput(BaseModel):
    inspection_type: str = Field(min_length=1, max_length=40)
    result: str
    inspector: str = Field(min_length=1, max_length=100)
    accepted_qty: Decimal = Field(default=Decimal("0"), ge=0)
    rejected_qty: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = None


class ReleaseInput(BaseModel):
    warehouse_code: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    released_by: str = Field(min_length=1, max_length=100)


class TraceInput(BaseModel):
    event_type: str
    actor: str = Field(min_length=1, max_length=100)
    serial_no: str | None = None
    reference_type: str | None = None
    reference_id: str | None = None
    notes: str | None = None


@router.post("/batches", status_code=201)
def create_batch(payload: BatchInput, _=Depends(require_permission("qc.execute"))):
    with _connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """INSERT INTO quality_batches
                    (batch_no, production_order_no, product_code, planned_qty)
                    VALUES (%s,%s,%s,%s)
                    RETURNING id, batch_no, production_order_no, product_code, planned_qty, status, created_at""",
                    (payload.batch_no, payload.production_order_no, payload.product_code, payload.planned_qty),
                )
                row = cur.fetchone()
                cur.execute(
                    """INSERT INTO traceability_events
                    (batch_no, product_code, production_order_no, event_type, actor, notes)
                    VALUES (%s,%s,%s,'CREATED',%s,'QC batch created')""",
                    (payload.batch_no, payload.product_code, payload.production_order_no, "system"),
                )
                conn.commit()
                return row
            except Exception as exc:
                conn.rollback()
                if "uq_quality_batch_no" in str(exc):
                    raise HTTPException(status_code=409, detail="batch_no already exists") from exc
                raise


@router.get("/batches/{batch_no}")
def get_batch(batch_no: str, _=Depends(require_permission("qc.read"))):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM quality_batches WHERE batch_no=%s", (batch_no,))
            batch = cur.fetchone()
            if not batch:
                raise HTTPException(status_code=404, detail="Quality batch not found")
            cur.execute(
                "SELECT * FROM quality_inspections WHERE quality_batch_id=%s ORDER BY inspected_at",
                (batch["id"],),
            )
            inspections = cur.fetchall()
            cur.execute(
                "SELECT * FROM quality_defects WHERE quality_batch_id=%s ORDER BY created_at",
                (batch["id"],),
            )
            defects = cur.fetchall()
            cur.execute(
                "SELECT * FROM finished_goods_releases WHERE quality_batch_id=%s ORDER BY released_at",
                (batch["id"],),
            )
            releases = cur.fetchall()
            return {"batch": batch, "inspections": inspections, "defects": defects, "releases": releases}


@router.post("/batches/{batch_no}/inspect")
def inspect_batch(batch_no: str, payload: InspectionInput, _=Depends(require_permission("qc.execute"))):
    result = payload.result.upper()
    if result not in {"PASS", "FAIL", "CONDITIONAL"}:
        raise HTTPException(status_code=422, detail="result must be PASS, FAIL or CONDITIONAL")
    if payload.accepted_qty + payload.rejected_qty <= 0:
        raise HTTPException(status_code=422, detail="inspection quantities must be positive")

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM quality_batches WHERE batch_no=%s FOR UPDATE", (batch_no,))
            batch = cur.fetchone()
            if not batch:
                raise HTTPException(status_code=404, detail="Quality batch not found")
            if batch["status"] in {"RELEASED", "BLOCKED"}:
                raise HTTPException(status_code=409, detail="released or blocked batch cannot be inspected")
            new_accepted = batch["accepted_qty"] + payload.accepted_qty
            new_rejected = batch["rejected_qty"] + payload.rejected_qty
            if new_accepted + new_rejected > batch["planned_qty"]:
                raise HTTPException(status_code=422, detail="inspection quantity exceeds planned quantity")
            next_status = "FAILED" if result == "FAIL" else ("PASSED" if result == "PASS" else "INSPECTION")
            cur.execute(
                """INSERT INTO quality_inspections
                (quality_batch_id, inspection_type, result, inspector, notes)
                VALUES (%s,%s,%s,%s,%s) RETURNING *""",
                (batch["id"], payload.inspection_type, result, payload.inspector, payload.notes),
            )
            inspection = cur.fetchone()
            cur.execute(
                """UPDATE quality_batches
                SET accepted_qty=%s, rejected_qty=%s, status=%s
                WHERE id=%s RETURNING *""",
                (new_accepted, new_rejected, next_status, batch["id"]),
            )
            updated = cur.fetchone()
            cur.execute(
                """INSERT INTO traceability_events
                (batch_no, product_code, production_order_no, event_type, actor, notes)
                VALUES (%s,%s,%s,%s,%s,%s)""",
                (batch_no, batch["product_code"], batch["production_order_no"], "QC_PASS" if result == "PASS" else "QC_FAIL" if result == "FAIL" else "QC_INSPECTION", payload.inspector, payload.notes),
            )
            conn.commit()
            return {"batch": updated, "inspection": inspection}


@router.post("/batches/{batch_no}/release", status_code=201)
def release_finished_goods(batch_no: str, payload: ReleaseInput, _=Depends(require_permission("qc.release"))):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM quality_batches WHERE batch_no=%s FOR UPDATE", (batch_no,))
            batch = cur.fetchone()
            if not batch:
                raise HTTPException(status_code=404, detail="Quality batch not found")
            if batch["status"] != "PASSED":
                raise HTTPException(status_code=409, detail="only PASSED batches can be released")
            if payload.quantity > batch["accepted_qty"]:
                raise HTTPException(status_code=422, detail="release quantity exceeds accepted quantity")
            cur.execute("SELECT 1 FROM finished_goods_releases WHERE quality_batch_id=%s", (batch["id"],))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="finished goods already released for batch")
            cur.execute(
                """INSERT INTO finished_goods_releases
                (quality_batch_id, product_code, warehouse_code, quantity, released_by)
                VALUES (%s,%s,%s,%s,%s) RETURNING *""",
                (batch["id"], batch["product_code"], payload.warehouse_code, payload.quantity, payload.released_by),
            )
            release = cur.fetchone()
            cur.execute(
                """UPDATE quality_batches SET status='RELEASED', released_at=CURRENT_TIMESTAMP, released_by=%s WHERE id=%s""",
                (payload.released_by, batch["id"]),
            )
            cur.execute(
                """INSERT INTO traceability_events
                (batch_no, product_code, production_order_no, event_type, reference_type, reference_id, actor, notes)
                VALUES (%s,%s,%s,'RELEASE','FINISHED_GOODS_RELEASE',%s,%s,'Finished goods released')""",
                (batch_no, batch["product_code"], batch["production_order_no"], str(release["id"]), payload.released_by),
            )
            conn.commit()
            return release


@router.post("/batches/{batch_no}/trace")
def add_trace_event(batch_no: str, payload: TraceInput, _=Depends(require_permission("qc.execute"))):
    allowed = {"CREATED", "OPERATION", "QC_INSPECTION", "QC_PASS", "QC_FAIL", "RELEASE", "SHIPMENT", "RETURN", "SCRAP"}
    if payload.event_type.upper() not in allowed:
        raise HTTPException(status_code=422, detail="invalid trace event type")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT product_code, production_order_no FROM quality_batches WHERE batch_no=%s", (batch_no,))
            batch = cur.fetchone()
            if not batch:
                raise HTTPException(status_code=404, detail="Quality batch not found")
            cur.execute(
                """INSERT INTO traceability_events
                (batch_no, serial_no, product_code, production_order_no, event_type, reference_type, reference_id, actor, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (batch_no, payload.serial_no, batch["product_code"], batch["production_order_no"], payload.event_type.upper(), payload.reference_type, payload.reference_id, payload.actor, payload.notes),
            )
            row = cur.fetchone()
            conn.commit()
            return row


@router.get("/trace/{batch_no}")
def trace_batch(batch_no: str, _=Depends(require_permission("qc.read"))):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM traceability_events WHERE batch_no=%s ORDER BY event_at, id", (batch_no,))
            return {"batch_no": batch_no, "events": cur.fetchall()}
