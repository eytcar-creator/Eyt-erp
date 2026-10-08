from __future__ import annotations
import json
import re
from decimal import Decimal
from typing import Any
from fastapi import HTTPException

SUPPORTED_TYPES = {"PRODUCTION"}

def _safe_doc_no(message_id: str) -> str:
    return "RUBIKA-" + re.sub(r"[^a-zA-Z0-9]", "", message_id)[:32]

def _require_single_product(draft: dict[str, Any]) -> dict[str, Any]:
    if draft.get("status") != "DRAFT_REQUIRES_REVIEW":
        raise HTTPException(409, "Draft is not awaiting review")
    if draft.get("product_match_status") != "LIVE_MASTER_MATCH":
        raise HTTPException(422, "Exact live Product Master match is required")
    candidates = draft.get("entity_candidates") or []
    if len(candidates) != 1:
        raise HTTPException(422, "Exactly one Product Master match is required")
    product = candidates[0]
    if not product.get("product_id") or not product.get("product_code"):
        raise HTTPException(422, "Product Master UUID and SKU are required")
    if draft.get("quantity") is None or Decimal(str(draft["quantity"])) <= 0:
        raise HTTPException(422, "Positive production quantity is required")
    return product

def post_approved_production(cur: Any, message_id: str, extracted: dict[str, Any], actor_id: str) -> dict[str, Any]:
    draft = extracted.get("draft") or {}
    if extracted.get("message_type") not in SUPPORTED_TYPES:
        raise HTTPException(422, "This message type has no controlled ERP posting route yet")
    product = _require_single_product(draft)
    cur.execute("""SELECT status, extracted_data FROM rubika_workshop_messages
                   WHERE id=%s FOR UPDATE""", (message_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Workshop message not found")
    if row[0] != "APPROVED_PENDING_ERP":
        raise HTTPException(409, "Workshop message is not approved for ERP posting")

    key = f"rubika-erp:{message_id}:PRODUCTION"
    doc_no = _safe_doc_no(message_id)
    cur.execute("""SELECT erp_document_no, erp_reference_id, status
                   FROM rubika_workshop_erp_posts
                   WHERE idempotency_key=%s FOR UPDATE""", (key,))
    existing = cur.fetchone()
    if existing:
        return {"status": existing[2], "documentNo": existing[0], "referenceId": existing[1], "duplicate": True}

    cur.execute("""SELECT id, product_code, product_name_fa, is_active
                   FROM eyt_product_master WHERE product_code=%s""", (product["product_code"],))
    master = cur.fetchone()
    if not master or not master[3]:
        raise HTTPException(422, "Matched Product Master is not active")
    if product["product_code"] != master[1]:
        raise HTTPException(409, "Product Master changed after approval; re-review required")

    qty = Decimal(str(draft["quantity"]))
    cur.execute("""INSERT INTO inventory_transactions
        (document_no, warehouse_code, product_code, quantity, unit, transaction_type,
         reference_type, reference_id, unit_cost)
        VALUES (%s,'MAIN',%s,%s,'PCS','PRODUCTION_RECEIPT','RUBIKA_WORKSHOP',%s,0)
        RETURNING id""", (doc_no, master[1], qty, message_id))
    tx_id = cur.fetchone()[0]

    cur.execute("""INSERT INTO rubika_workshop_erp_posts
        (workshop_message_id,idempotency_key,erp_document_type,erp_document_no,
         erp_reference_id,status,posted_by)
        VALUES (%s,%s,'PRODUCTION_RECEIPT',%s,%s,'POSTED',%s)
        RETURNING id""", (message_id, key, doc_no, str(tx_id), actor_id))
    post_id = cur.fetchone()[0]

    cur.execute("""UPDATE rubika_workshop_messages
        SET status='ERP_POSTED', processed_at=NOW(), processing_error=NULL
        WHERE id=%s""", (message_id,))
    return {"status":"ERP_POSTED","documentNo":doc_no,"referenceId":str(tx_id),"postId":str(post_id),"duplicate":False}
