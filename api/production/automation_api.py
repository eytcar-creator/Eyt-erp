from typing import Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query
from psycopg.types.json import Json

from .auth import require_permission

router = APIRouter(prefix="/api/v1/automation", tags=["automation"])


def _db():
    import os
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)


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
    return [
        {
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
        for row in rows
    ]


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
                attempts=attempts+1,
                available_at=now() + interval '1 minute',
                last_error=%s,
                locked_at=NULL,
                locked_by=NULL
            WHERE id=%s
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
