from typing import Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from psycopg.types.json import Json

from .auth import require_permission

router = APIRouter(prefix="/api/v1/automation", tags=["automation"])


def _db():
    import os
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)


class EffectReserveInput(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=300)
    event_id: UUID | None = None
    channel: str = Field(min_length=1, max_length=80)
    action_code: str = Field(min_length=1, max_length=120)


class EffectCompleteInput(BaseModel):
    provider_message_id: str | None = Field(default=None, max_length=300)
    response_payload: dict[str, Any] = Field(default_factory=dict)


class EffectFailInput(BaseModel):
    error: str = Field(min_length=1, max_length=2000)


def _event(row) -> dict[str, Any]:
    return {
        "id": row[0],
        "event_type": row[1],
        "aggregate_type": row[2],
        "aggregate_id": row[3],
        "source_table": row[4],
        "payload": row[5],
        "status": row[6],
        "attempts": row[7],
        "available_at": row[8],
        "created_at": row[9],
    }


@router.get("/events")
def list_events(
    limit: int = Query(default=50, ge=1, le=200),
    principal: dict = Depends(require_permission("automation.read")),
) -> list[dict[str, Any]]:
    del principal
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT id,event_type,aggregate_type,aggregate_id,source_table,payload,
                   status,attempts,available_at,created_at
            FROM eyt_automation_events
            WHERE status='PENDING' AND available_at <= now()
            ORDER BY created_at
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [_event(row) for row in rows]


@router.post("/events/claim")
def claim_events(
    limit: int = Query(default=20, ge=1, le=100),
    worker: str = Query(default="n8n", min_length=1, max_length=120),
    principal: dict = Depends(require_permission("automation.write")),
) -> list[dict[str, Any]]:
    del principal
    with _db() as conn:
        rows = conn.execute(
            """
            WITH picked AS (
                SELECT id
                FROM eyt_automation_events
                WHERE status='PENDING' AND available_at <= now()
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT %s
            )
            UPDATE eyt_automation_events e
            SET status='PROCESSING', locked_at=now(), locked_by=%s, attempts=attempts+1
            FROM picked
            WHERE e.id=picked.id
            RETURNING e.id,e.event_type,e.aggregate_type,e.aggregate_id,e.source_table,
                      e.payload,e.status,e.attempts,e.available_at,e.created_at
            """,
            (limit, worker),
        ).fetchall()
        conn.commit()
    return [_event(row) for row in rows]


@router.post("/effects/reserve")
def reserve_effect(
    payload: EffectReserveInput,
    principal: dict = Depends(require_permission("automation.write")),
) -> dict[str, Any]:
    del principal
    with _db() as conn:
        row = conn.execute(
            """
            INSERT INTO eyt_automation_effects(
                idempotency_key,event_id,channel,action_code,status
            )
            VALUES(%s,%s,%s,%s,'PROCESSING')
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id,idempotency_key,event_id,channel,action_code,status,
                      provider_message_id,response_payload,created_at,updated_at
            """,
            (
                payload.idempotency_key,
                payload.event_id,
                payload.channel,
                payload.action_code,
            ),
        ).fetchone()
        created = row is not None
        if not row:
            row = conn.execute(
                """
                SELECT id,idempotency_key,event_id,channel,action_code,status,
                       provider_message_id,response_payload,created_at,updated_at
                FROM eyt_automation_effects
                WHERE idempotency_key=%s
                FOR UPDATE
                """,
                (payload.idempotency_key,),
            ).fetchone()
        conn.commit()
    return {
        "id": row[0],
        "idempotency_key": row[1],
        "event_id": row[2],
        "channel": row[3],
        "action_code": row[4],
        "status": row[5],
        "provider_message_id": row[6],
        "response_payload": row[7],
        "created_at": row[8],
        "updated_at": row[9],
        "reserved": created,
        "should_send": created,
    }


@router.post("/effects/{effect_id}/complete")
def complete_effect(
    effect_id: UUID,
    payload: EffectCompleteInput,
    principal: dict = Depends(require_permission("automation.write")),
) -> dict[str, Any]:
    del principal
    with _db() as conn:
        row = conn.execute(
            """
            UPDATE eyt_automation_effects
            SET status='SENT',
                provider_message_id=%s,
                response_payload=%s,
                last_error=NULL,
                updated_at=now(),
                completed_at=now()
            WHERE id=%s AND status='PROCESSING'
            RETURNING id,status,provider_message_id,completed_at
            """,
            (payload.provider_message_id, Json(payload.response_payload), effect_id),
        ).fetchone()
        conn.commit()
    if not row:
        return {"id": effect_id, "status": "not_completed"}
    return {
        "id": row[0],
        "status": row[1],
        "provider_message_id": row[2],
        "completed_at": row[3],
    }


@router.post("/effects/{effect_id}/fail")
def fail_effect(
    effect_id: UUID,
    payload: EffectFailInput,
    principal: dict = Depends(require_permission("automation.write")),
) -> dict[str, Any]:
    del principal
    with _db() as conn:
        row = conn.execute(
            """
            UPDATE eyt_automation_effects
            SET status='FAILED', last_error=%s, updated_at=now()
            WHERE id=%s AND status='PROCESSING'
            RETURNING id,status,last_error,updated_at
            """,
            (payload.error, effect_id),
        ).fetchone()
        conn.commit()
    if not row:
        return {"id": effect_id, "status": "not_failed"}
    return {
        "id": row[0],
        "status": row[1],
        "last_error": row[2],
        "updated_at": row[3],
    }


@router.post("/events/{event_id}/ack")
def acknowledge_event(
    event_id: UUID,
    principal: dict = Depends(require_permission("automation.write")),
) -> dict[str, Any]:
    del principal
    with _db() as conn:
        row = conn.execute(
            """
            UPDATE eyt_automation_events
            SET status='DELIVERED', delivered_at=now(), locked_at=NULL, locked_by=NULL
            WHERE id=%s AND status IN ('PENDING','PROCESSING')
            RETURNING id,status,delivered_at
            """,
            (event_id,),
        ).fetchone()
        conn.commit()
    if not row:
        return {"id": event_id, "status": "not_acknowledged"}
    return {"id": row[0], "status": row[1], "delivered_at": row[2]}


@router.post("/events/{event_id}/fail")
def fail_event(
    event_id: UUID,
    error: str = Query(default="", max_length=2000),
    principal: dict = Depends(require_permission("automation.write")),
) -> dict[str, Any]:
    del principal
    with _db() as conn:
        row = conn.execute(
            """
            UPDATE eyt_automation_events
            SET status='PENDING',
                available_at=now() + interval '1 minute',
                last_error=%s,
                locked_at=NULL,
                locked_by=NULL
            WHERE id=%s AND status='PROCESSING'
            RETURNING id,status,attempts,available_at
            """,
            (error, event_id),
        ).fetchone()
        conn.commit()
    if not row:
        return {"id": event_id, "status": "not_found"}
    return {
        "id": row[0],
        "status": row[1],
        "attempts": row[2],
        "available_at": row[3],
    }
