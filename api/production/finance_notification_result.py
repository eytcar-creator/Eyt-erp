from __future__ import annotations

from datetime import datetime, timedelta
import os
import psycopg


MAX_ATTEMPTS = 5


def db():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)


def mark_sent(event_id: int, worker_id: str) -> bool:
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE finance_notification_outbox
            SET status='SENT',
                sent_at=CURRENT_TIMESTAMP,
                locked_by=NULL,
                processing_started_at=NULL,
                last_error=NULL
            WHERE id=%s AND status='PROCESSING' AND locked_by=%s
            """,
            (event_id, worker_id),
        )
        changed = cur.rowcount == 1
        conn.commit()
    return changed


def mark_failed(event_id: int, worker_id: str, error: str) -> bool:
    safe_error = (error or "notification delivery failed")[:1000]
    with db() as conn, conn.cursor() as cur:
        row = cur.execute(
            """
            SELECT attempts
            FROM finance_notification_outbox
            WHERE id=%s AND status='PROCESSING' AND locked_by=%s
            FOR UPDATE
            """,
            (event_id, worker_id),
        ).fetchone()
        if not row:
            conn.rollback()
            return False

        attempts = row[0] + 1
        terminal = attempts >= MAX_ATTEMPTS
        if terminal:
            cur.execute(
                """
                UPDATE finance_notification_outbox
                SET status='FAILED',
                    attempts=%s,
                    last_error=%s,
                    locked_by=NULL,
                    processing_started_at=NULL
                WHERE id=%s AND status='PROCESSING' AND locked_by=%s
                """,
                (attempts, safe_error, event_id, worker_id),
            )
        else:
            delay_seconds = {1: 60, 2: 300, 3: 900, 4: 3600}.get(
                attempts, 3600
            )
            cur.execute(
                """
                UPDATE finance_notification_outbox
                SET status='PENDING',
                    attempts=%s,
                    last_error=%s,
                    available_at=CURRENT_TIMESTAMP + (%s * INTERVAL '1 second'),
                    locked_by=NULL,
                    processing_started_at=NULL
                WHERE id=%s AND status='PROCESSING' AND locked_by=%s
                """,
                (
                    attempts,
                    safe_error,
                    delay_seconds,
                    event_id,
                    worker_id,
                ),
            )
        changed = cur.rowcount == 1
        conn.commit()
    return changed
