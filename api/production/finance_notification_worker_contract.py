from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg


@dataclass(frozen=True)
class ClaimedEvent:
    id: int
    event_type: str
    entity_type: str
    entity_id: str
    payload: dict
    attempts: int


def db() -> psycopg.Connection:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)


def claim_batch(worker_id: str, limit: int = 25) -> list[ClaimedEvent]:
    """Atomically claim pending outbox events.

    This function only changes delivery-state metadata. It does not touch
    invoices, payments, receivables, or any other financial ledger.
    """
    if not worker_id:
        raise ValueError("worker_id is required")
    limit = max(1, min(limit, 100))

    with db() as conn, conn.cursor() as cur:
        rows = cur.execute(
            """
            WITH candidates AS (
              SELECT id
              FROM finance_notification_outbox
              WHERE status = 'PENDING'
                AND available_at <= CURRENT_TIMESTAMP
              ORDER BY id
              FOR UPDATE SKIP LOCKED
              LIMIT %s
            )
            UPDATE finance_notification_outbox o
            SET status = 'PROCESSING',
                locked_by = %s,
                processing_started_at = CURRENT_TIMESTAMP
            FROM candidates c
            WHERE o.id = c.id
            RETURNING o.id,o.event_type,o.entity_type,o.entity_id,
                      o.payload,o.attempts
            """,
            (limit, worker_id),
        ).fetchall()
        conn.commit()

    return [
        ClaimedEvent(
            id=row[0],
            event_type=row[1],
            entity_type=row[2],
            entity_id=row[3],
            payload=row[4],
            attempts=row[5],
        )
        for row in rows
    ]


def retry_delay(attempt: int) -> timedelta:
    """Bounded exponential retry delay."""
    schedule = {1: 60, 2: 300, 3: 900, 4: 3600}
    return timedelta(seconds=schedule.get(attempt, 3600))


def reclaim_stale_events(stale_after_minutes: int = 30) -> int:
    """Return abandoned PROCESSING events to PENDING."""
    cutoff = datetime.utcnow() - timedelta(minutes=stale_after_minutes)
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE finance_notification_outbox
            SET status='PENDING',
                locked_by=NULL,
                processing_started_at=NULL,
                available_at=CURRENT_TIMESTAMP
            WHERE status='PROCESSING'
              AND processing_started_at < %s
            """,
            (cutoff,),
        )
        changed = cur.rowcount
        conn.commit()
    return changed
