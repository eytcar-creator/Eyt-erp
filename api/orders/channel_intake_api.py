from __future__ import annotations

import hashlib
import hmac
import json
import os
from decimal import Decimal
from typing import Any

import psycopg
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .order_center import OrderChannel

router = APIRouter(prefix="/api/v1/channel-intake", tags=["E.Y.T One - Channel Hub"])

SUPPORTED_CHANNELS = {c.value for c in OrderChannel}


class IntakeItem(BaseModel):
    product_id: str | None = None
    product_code: str | None = None
    quantity: Decimal = Field(gt=0)


class ChannelIntakeIn(BaseModel):
    channel: str
    external_message_id: str | None = None
    idempotency_key: str | None = None
    customer_id: str | None = None
    text: str | None = None
    warehouse_code: str = "MAIN"
    items: list[IntakeItem] = Field(default_factory=list)
    requested_delivery_date: str | None = None
    payment_mode: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return psycopg.connect(url)


def _verify_signature(raw_body: bytes, signature: str | None) -> None:
    secret = os.environ.get("CHANNEL_INTAKE_SECRET")
    if not secret:
        return
    if not signature:
        raise HTTPException(status_code=401, detail="missing channel signature")
    supplied = signature.removeprefix("sha256=")
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="invalid channel signature")


@router.post("", status_code=201)
def receive_intake(
    payload: ChannelIntakeIn,
    x_channel_signature: str | None = Header(default=None),
) -> dict[str, Any]:
    if payload.channel not in SUPPORTED_CHANNELS:
        raise HTTPException(status_code=422, detail=f"unsupported channel: {payload.channel}")

    raw = payload.model_dump(mode="json")
    raw_bytes = json.dumps(raw, separators=(",", ":"), ensure_ascii=False).encode()
    _verify_signature(raw_bytes, x_channel_signature)

    with _db() as conn:
        with conn.cursor() as cur:
            if payload.idempotency_key:
                cur.execute(
                    "SELECT id, status, order_no FROM channel_intakes WHERE idempotency_key=%s",
                    (payload.idempotency_key,),
                )
                existing = cur.fetchone()
                if existing:
                    return {
                        "intake_id": str(existing[0]),
                        "status": existing[1],
                        "order_no": existing[2],
                        "duplicate": True,
                    }

            if payload.external_message_id:
                cur.execute(
                    "SELECT id, status, order_no FROM channel_intakes "
                    "WHERE channel=%s AND external_message_id=%s",
                    (payload.channel, payload.external_message_id),
                )
                existing = cur.fetchone()
                if existing:
                    return {
                        "intake_id": str(existing[0]),
                        "status": existing[1],
                        "order_no": existing[2],
                        "duplicate": True,
                    }

            errors: list[str] = []
            resolved: list[dict[str, Any]] = []

            if not payload.customer_id:
                errors.append("customer_id is required before order confirmation")
            elif payload.items:
                cur.execute(
                    "SELECT id FROM customers WHERE id=%s",
                    (payload.customer_id,),
                )
                if not cur.fetchone():
                    errors.append(f"customer not found: {payload.customer_id}")

            for item in payload.items:
                product_id = item.product_id
                if product_id:
                    cur.execute(
                        "SELECT id, product_code, is_active FROM products WHERE id=%s",
                        (product_id,),
                    )
                elif item.product_code:
                    cur.execute(
                        "SELECT id, product_code, is_active FROM products WHERE product_code=%s",
                        (item.product_code,),
                    )
                else:
                    cur.execute("SELECT NULL::uuid, NULL::text, FALSE WHERE FALSE")

                product = cur.fetchone()
                if not product or not product[2]:
                    errors.append(
                        f"active product not found: {item.product_id or item.product_code}"
                    )
                else:
                    resolved.append(
                        {
                            "product_id": str(product[0]),
                            "product_code": product[1],
                            "quantity": str(item.quantity),
                        }
                    )

            status = "PENDING_CONFIRMATION" if not errors and payload.items else "RECEIVED"
            cur.execute(
                """
                INSERT INTO channel_intakes
                  (channel, external_message_id, idempotency_key, customer_id,
                   raw_text, payload, status, validation_errors, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,NOW(),NOW())
                RETURNING id
                """,
                (
                    payload.channel,
                    payload.external_message_id,
                    payload.idempotency_key,
                    payload.customer_id,
                    payload.text,
                    json.dumps(raw, ensure_ascii=False),
                    status,
                    json.dumps(errors, ensure_ascii=False),
                ),
            )
            intake_id = str(cur.fetchone()[0])
        conn.commit()

    return {
        "intake_id": intake_id,
        "order_no": None,
        "status": status,
        "customer_match": bool(payload.customer_id and not any("customer" in e for e in errors)),
        "product_matches": resolved,
        "validation_errors": errors,
        "next_action": (
            "CUSTOMER_CONFIRMATION" if status == "PENDING_CONFIRMATION"
            else "RESOLVE_CUSTOMER_AND_PRODUCTS"
        ),
    }
