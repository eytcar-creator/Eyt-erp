import hashlib
import json
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from api.rubika_workshop_extraction import extract_message

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
        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if value not in (None, ""):
            return value
    return None


def _classify(text: str) -> str:
    return extract_message(text)["message_type"]


def _extract(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(_first(
        payload,
        ("message", "text"), ("message", "body"),
        ("data", "message", "text"), ("update", "message", "text"), ("text",),
    ) or "").strip()
    external_id = _first(
        payload, ("message", "message_id"), ("message", "id"),
        ("data", "message", "message_id"), ("update", "message", "message_id"), ("id",),
    )
    chat_id = _first(
        payload, ("message", "chat_id"), ("message", "chat", "chat_id"),
        ("data", "chat_id"), ("update", "chat_id"),
    )
    sender_id = _first(
        payload, ("message", "sender_id"), ("message", "sender", "user_id"),
        ("data", "sender_id"), ("update", "sender_id"),
    )
    sender_name = _first(
        payload, ("message", "sender", "name"), ("message", "sender", "first_name"),
        ("data", "sender_name"), ("update", "sender_name"),
    )
    return {
        "external_message_id": str(external_id) if external_id is not None else None,
        "chat_id": str(chat_id) if chat_id is not None else None,
        "sender_id": str(sender_id) if sender_id is not None else None,
        "sender_name": str(sender_name) if sender_name is not None else None,
        "message_text": text,
        "message_type": _classify(text),
    }


def _db():
    database_url = os.getenv(DATABASE_URL_ENV)
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    import psycopg
    return psycopg.connect(database_url, connect_timeout=3)


def _persist_event(event: dict[str, Any], raw_payload: dict[str, Any]) -> bool:
    sql = """
        INSERT INTO rubika_workshop_messages (
            external_message_id, idempotency_key, chat_id, sender_id,
            sender_name, message_text, message_type, raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING id
    """
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                event["external_message_id"], event["idempotency_key"],
                event["chat_id"], event["sender_id"], event["sender_name"],
                event["message_text"], event["message_type"],
                json.dumps(raw_payload, ensure_ascii=False),
            ))
            inserted = cur.fetchone() is not None
        conn.commit()
    return inserted


def _extract_pending(limit: int = 50) -> list[dict[str, Any]]:
    sql = """
        SELECT id, external_message_id, chat_id, sender_name, message_text,
               message_type, received_at, status, extracted_data
        FROM rubika_workshop_messages
        WHERE status = 'RECEIVED'
        ORDER BY received_at ASC
        LIMIT %s
    """
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (max(1, min(limit, 200)),))
            rows = cur.fetchall()
    keys = ("id", "external_message_id", "chat_id", "sender_name",
            "message_text", "message_type", "received_at", "status", "extracted_data")
    return [dict(zip(keys, row)) for row in rows]


def _run_extraction(message_id: str) -> dict[str, Any]:
    sql = """
        SELECT message_text, message_type
        FROM rubika_workshop_messages
        WHERE id = %s
    """
    update = """
        UPDATE rubika_workshop_messages
        SET extracted_data = %s::jsonb,
            status = 'EXTRACTED_PENDING_APPROVAL',
            processed_at = NOW(),
            processing_error = NULL
        WHERE id = %s
    """
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (message_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Workshop message not found")
            proposal = extract_message(row[0] or "", row[1])
            cur.execute(update, (json.dumps(proposal, ensure_ascii=False), message_id))
        conn.commit()
    return proposal


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "rubika-workshop-gateway",
        "webhook_secret_configured": bool(os.getenv(WEBHOOK_SECRET_ENV)),
        "database_configured": bool(os.getenv(DATABASE_URL_ENV)),
        "ai_extraction": "v1-review-required",
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
        if event["external_message_id"] else f"rubika:sha256:{digest}"
    )
    try:
        inserted = _persist_event(event, payload)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to persist webhook event") from exc
    return {
        "ok": True, "accepted": True, "channel": "RUBIKA_WORKSHOP",
        "event": event, "stored": inserted, "duplicate": not inserted,
        "next_step": "AI_EXTRACTION", "erp_mutation": False,
    }


@router.get("/extraction/pending")
async def extraction_pending(limit: int = 50) -> dict[str, Any]:
    try:
        items = _extract_pending(limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to read extraction queue") from exc
    return {"ok": True, "count": len(items), "items": items}


@router.post("/extraction/{message_id}")
async def extract_one(message_id: str) -> dict[str, Any]:
    try:
        proposal = _run_extraction(message_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to extract workshop message") from exc
    return {
        "ok": True,
        "message_id": message_id,
        "status": "EXTRACTED_PENDING_APPROVAL",
        "proposal": proposal,
        "erp_mutation": False,
    }


@router.post("/extraction/{message_id}/approve")
async def approve_extraction(message_id: str) -> dict[str, Any]:
    sql = """
        UPDATE rubika_workshop_messages
        SET status = 'APPROVED_PENDING_ERP'
        WHERE id = %s AND status = 'EXTRACTED_PENDING_APPROVAL'
        RETURNING id, extracted_data
    """
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (message_id,))
                row = cur.fetchone()
            conn.commit()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to approve extraction") from exc
    if not row:
        raise HTTPException(status_code=409, detail="Message is not awaiting approval")
    return {
        "ok": True,
        "message_id": message_id,
        "status": "APPROVED_PENDING_ERP",
        "proposal": row[1],
        "erp_mutation": False,
        "next_step": "CONTROLLED_ERP_MUTATION",
    }
