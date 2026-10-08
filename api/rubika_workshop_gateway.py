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


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "rubika-workshop-gateway",
        "webhook_secret_configured": bool(os.getenv(WEBHOOK_SECRET_ENV)),
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

    # Raw-event persistence is intentionally isolated from canonical ERP mutation.
    # The production DB migration creates rubika_workshop_messages for this stage.
    return {
        "ok": True,
        "accepted": True,
        "channel": "RUBIKA_WORKSHOP",
        "event": event,
        "next_step": "AI_EXTRACTION",
        "erp_mutation": False,
    }
