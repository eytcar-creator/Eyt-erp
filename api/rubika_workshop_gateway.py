import hashlib
import json
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter(
    prefix="/api/v1/integrations/rubika/workshop",
    tags=["Rubika Workshop Gateway"],
)

WEBHOOK_SECRET_ENV = "RUBIKA_WORKSHOP_WEBHOOK_SECRET"
DATABASE_URL_ENV = "DATABASE_URL"


def _secret_ok(request: Request, supplied: str | None) -> bool:
    expected = os.getenv(WEBHOOK_SECRET_ENV)
    if not expected:
        return False
    header_secret = request.headers.get("X-Webhook-Secret")
    return supplied == expected or header_secret == expected


def _first(data: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        value: Any = data
        try:
            for key in path:
                if not isinstance(value, dict):
                    value = None
                    break
                value = value.get(key)
            if value not in (None, ""):
                return value
        except Exception:
            continue
    return None


def _classify(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ("پرداخت", "واریز", "تومان", "هزینه", "خرج")):
        return "PAYMENT"
    if any(x in t for x in ("تولید", "تعداد", "قالب", "تزریق", "پخت")):
        return "PRODUCTION"
    if any(x in t for x in ("مواد", "لاستیک", "کامپاند", "چسب", "لوله")):
        return "MATERIAL"
    if any(x in t for x in ("خرید", "سفارش", "قیمت خرید")):
        return "PURCHASE"
    if any(x in t for x in ("مشکل", "خراب", "نشد", "کمبود", "ایراد")):
        return "ISSUE"
    return "GENERAL"


def _extract(payload: dict[str, Any]) -> dict[str, Any]:
    text = _first(
        payload,
        ("message", "text"),
        ("message", "body"),
        ("data", "message", "text"),
        ("update", "message", "text"),
        ("text",),
    )
    text = str(text or "").strip()

    external_id = _first(
        payload,
        ("message", "message_id"),
        ("message", "id"),
        ("data", "message", "message_id"),
        ("update", "message", "message_id"),
        ("id",),
    )
    chat_id = _first(
        payload,
        ("message", "chat_id"),
        ("message", "chat", "chat_id"),
        ("data", "chat_id"),
        ("update", "chat_id"),
    )
    sender_id = _first(
        payload,
        ("message", "sender_id"),
        ("message", "sender", "user_id"),
        ("data", "sender_id"),
        ("update", "sender_id"),
    )
    sender_name = _first(
        payload,
        ("message", "sender", "name"),
        ("message", "sender", "first_name"),
        ("data", "sender_name"),
        ("update", "sender_name"),
    )

    return {
        "external_message_id": str(external_id) if external_id is not None else None,
        "chat_id": str(chat_id) if chat_id is not None else None,
        "sender_id": str(sender_id) if sender_id is not None else None,
        "sender_name": str(sender_name) if sender_name is not None else None,
        "message_text": text,
        "message_type": _classify(text),
    }


def _persist_event(event: dict[str, Any], raw_payload: dict[str, Any]) -> bool:
    database_url = os.getenv(DATABASE_URL_ENV)
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    import psycopg

    sql = """
        INSERT INTO rubika_workshop_messages (
            external_message_id,
            idempotency_key,
            chat_id,
            sender_id,
            sender_name,
            message_text,
            message_type,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING id
    """
    with psycopg.connect(database_url, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    event["external_message_id"],
                    event["idempotency_key"],
                    event["chat_id"],
                    event["sender_id"],
                    event["sender_name"],
                    event["message_text"],
                    event["message_type"],
                    json.dumps(raw_payload, ensure_ascii=False),
                ),
            )
            inserted = cur.fetchone() is not None
        conn.commit()
    return inserted


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "rubika-workshop-gateway",
        "webhook_secret_configured": bool(os.getenv(WEBHOOK_SECRET_ENV)),
        "database_configured": bool(os.getenv(DATABASE_URL_ENV)),
    }


@router.post("/webhook")
async def webhook(
    request: Request,
    secret: str | None = None,
    x_webhook_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    supplied = secret or x_webhook_secret
    if not _secret_ok(request, supplied):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    event = _extract(payload)
    digest = hashlib.sha256(raw).hexdigest()
    event["idempotency_key"] = (
        f"rubika:{event['external_message_id']}"
        if event["external_message_id"]
        else f"rubika:sha256:{digest}"
    )

    try:
        inserted = _persist_event(event, payload)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to persist webhook event") from exc

    return {
        "ok": True,
        "accepted": True,
        "channel": "RUBIKA_WORKSHOP",
        "event": event,
        "stored": inserted,
        "duplicate": not inserted,
        "next_step": "AI_EXTRACTION",
        "erp_mutation": False,
    }
