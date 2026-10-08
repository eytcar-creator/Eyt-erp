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

from .order_center import CreateOrder, OrderChannel, OrderLine, PaymentType
from . import fastapi_router as order_api
from .commercial_gate import CommercialGate, CommercialLine

router = APIRouter(prefix="/api/v1/channel-intake", tags=["E.Y.T One - Channel Hub"])

SUPPORTED_CHANNELS = {c.value for c in OrderChannel}


class IntakeItem(BaseModel):
    product_id: str | None = None
    product_code: str | None = None
    quantity: Decimal = Field(gt=0)


class CustomerConfirmationIn(BaseModel):
    confirmation_id: str = Field(min_length=8, max_length=200)
    proposal_fingerprint: str = Field(min_length=64, max_length=64)
    confirmation_source: str = Field(min_length=2, max_length=80)
    confirmation_actor: str = Field(min_length=1, max_length=200)


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


def _proposal_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(canonical).hexdigest()


def _verify_signature(raw_body: bytes, signature: str | None, channel_token: str | None = None) -> None:
    internal_token = os.environ.get("EYT_ERP_CHANNEL_TOKEN")
    if internal_token and channel_token and hmac.compare_digest(channel_token, internal_token):
        return
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
    x_channel_token: str | None = Header(default=None),
) -> dict[str, Any]:
    if payload.channel not in SUPPORTED_CHANNELS:
        raise HTTPException(status_code=422, detail=f"unsupported channel: {payload.channel}")

    raw = payload.model_dump(mode="json")
    raw_bytes = json.dumps(raw, separators=(",", ":"), ensure_ascii=False).encode()
    _verify_signature(raw_bytes, x_channel_signature, x_channel_token)

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
            # Persist resolved product IDs so confirmation never has to guess again.
            if not errors:
                raw["items"] = resolved
            proposal_fingerprint = _proposal_fingerprint(raw)
            cur.execute(
                """
                INSERT INTO channel_intakes
                  (channel, external_message_id, idempotency_key, customer_id,
                   raw_text, payload, status, validation_errors, proposal_fingerprint, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s,NOW(),NOW())
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
                    proposal_fingerprint,
                ),
            )
            intake_id = str(cur.fetchone()[0])
        conn.commit()

    return {
        "intake_id": intake_id,
        "order_no": None,
        "status": status,
        "proposal_fingerprint": proposal_fingerprint,
        "customer_match": bool(payload.customer_id and not any("customer" in e for e in errors)),
        "product_matches": resolved,
        "validation_errors": errors,
        "next_action": (
            "CUSTOMER_CONFIRMATION" if status == "PENDING_CONFIRMATION"
            else "RESOLVE_CUSTOMER_AND_PRODUCTS"
        ),
    }


@router.post("/{intake_id}/confirm")
def confirm_intake(
    intake_id: str,
    confirmation: CustomerConfirmationIn,
    x_channel_signature: str | None = Header(default=None),
    x_channel_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Convert a validated intake into the canonical sales order and confirm it.

    The ERP Order Center remains the only component allowed to reserve stock,
    apply credit controls and transition the order to RESERVED.
    """
    raw = intake_id.encode()
    _verify_signature(raw, x_channel_signature, x_channel_token)

    if order_api.order_center is None:
        raise HTTPException(status_code=503, detail="Order Center is not configured")

    # Explicit channel confirmation is the final customer confirmation step.
    # Re-run the commercial gate immediately before mutation so price, stock and
    # credit are validated against current state, not stale proposal data.
    gate = CommercialGate()

    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, channel, customer_id, payload, status, order_no, "
                "proposal_fingerprint, confirmation_id "
                "FROM channel_intakes WHERE id=%s FOR UPDATE",
                (intake_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="channel intake not found")

            if row[4] == "CONVERTED" and row[5]:
                return {"intake_id": str(row[0]), "order_no": row[5], "status": "CONVERTED", "duplicate": True}

            if row[4] != "PENDING_CONFIRMATION":
                raise HTTPException(status_code=409, detail=f"intake is not confirmable: {row[4]}")

            data = row[3] or {}
            items = data.get("items") or []
            current_fingerprint = _proposal_fingerprint(data)
            if row[6] != confirmation.proposal_fingerprint or current_fingerprint != confirmation.proposal_fingerprint:
                raise HTTPException(
                    status_code=409,
                    detail={"status": "PROPOSAL_CHANGED", "current_fingerprint": current_fingerprint},
                )
            if not row[2] or not items:
                raise HTTPException(status_code=409, detail="intake has no confirmed customer/items")

            try:
                channel = OrderChannel(row[1])
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"unsupported order channel: {row[1]}") from exc

            payment_raw = str(data.get("payment_mode") or "CASH").upper()
            payment_type = PaymentType.CREDIT if payment_raw == PaymentType.CREDIT.value else PaymentType.CASH
            warehouse_code = str(data.get("warehouse_code") or "MAIN")

            gate_result = gate.evaluate(
                customer_id=str(row[2]),
                warehouse_code=warehouse_code,
                payment_type=payment_type.value,
                items=tuple(
                    CommercialLine(product_id=str(item.get("product_id")), quantity=Decimal(str(item.get("quantity"))))
                    for item in items
                    if item.get("product_id") and item.get("quantity")
                ),
            )
            if gate_result["gate_status"] != "PASS":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "commercial gate did not pass",
                        "gate": gate_result,
                    },
                )

            lines: list[OrderLine] = []
            for item in items:
                product_id = item.get("product_id")
                quantity = item.get("quantity")
                if not product_id or not quantity:
                    raise HTTPException(status_code=409, detail="intake contains unresolved product lines")
                # Price is resolved by the canonical Order Center HTTP pricing path.
                # This internal conversion therefore reuses the same price tables directly.
                cur.execute(
                    "SELECT sale_price FROM products WHERE id=%s AND is_active=TRUE",
                    (product_id,),
                )
                product = cur.fetchone()
                if not product:
                    raise HTTPException(status_code=422, detail=f"active product not found: {product_id}")
                cur.execute(
                    """SELECT pli.unit_price
                       FROM customers c
                       JOIN price_lists pl ON pl.id=c.default_price_list_id AND pl.active=TRUE
                       JOIN price_list_items pli ON pli.price_list_id=pl.id AND pli.product_id=%s
                       WHERE c.id=%s AND pli.active=TRUE AND pli.min_quantity<=%s
                         AND pli.valid_from<=CURRENT_TIMESTAMP
                         AND (pli.valid_to IS NULL OR pli.valid_to>CURRENT_TIMESTAMP)
                         AND (pl.valid_to IS NULL OR pl.valid_to>CURRENT_TIMESTAMP)
                       ORDER BY pli.min_quantity DESC, pli.valid_from DESC LIMIT 1""",
                    (product_id, row[2], quantity),
                )
                price_row = cur.fetchone()
                unit_price = Decimal(str(price_row[0] if price_row else product[0] or 0))
                if unit_price <= 0:
                    raise HTTPException(status_code=422, detail=f"product has no valid sale price: {product_id}")
                lines.append(OrderLine(product_id=str(product_id), quantity=Decimal(str(quantity)), unit_price=unit_price))

    created = order_api.order_center.create(CreateOrder(
        customer_id=str(row[2]),
        warehouse_code=warehouse_code,
        channel=channel,
        items=tuple(lines),
        idempotency_key=f"channel-intake:{intake_id}",
        payment_type=payment_type,
        notes=f"E.Y.T One intake {intake_id}",
    ))
    order_no = created["order_no"]
    confirmed = order_api.order_center.confirm(order_no)

    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE channel_intakes
                   SET status='CONVERTED', order_no=%s, confirmed_at=NOW(),
                       confirmation_id=%s, confirmation_source=%s,
                       confirmation_actor=%s, updated_at=NOW()
                   WHERE id=%s""",
                (order_no, confirmation.confirmation_id, confirmation.confirmation_source,
                 confirmation.confirmation_actor, intake_id),
            )
        conn.commit()

    return {
        "intake_id": intake_id,
        "order_no": order_no,
        "status": "CONVERTED",
        "confirmation": {
            "confirmation_id": confirmation.confirmation_id,
            "confirmation_source": confirmation.confirmation_source,
            "confirmation_actor": confirmation.confirmation_actor,
            "proposal_fingerprint": confirmation.proposal_fingerprint,
        },
        "order": confirmed,
    }
