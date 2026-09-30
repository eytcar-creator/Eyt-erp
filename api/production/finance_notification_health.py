from __future__ import annotations

import os
import psycopg


def db():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)


def queue_health() -> dict:
    with db() as conn:
        row = conn.execute(
            """
            SELECT
              COUNT(*) FILTER (WHERE status='PENDING')::int,
              COUNT(*) FILTER (WHERE status='PROCESSING')::int,
              COUNT(*) FILTER (WHERE status='SENT')::int,
              COUNT(*) FILTER (WHERE status='FAILED')::int,
              COUNT(*) FILTER (
                WHERE status='PROCESSING'
                  AND processing_started_at < CURRENT_TIMESTAMP - INTERVAL '30 minutes'
              )::int
            FROM finance_notification_outbox
            """
        ).fetchone()

    return {
        "pending": row[0],
        "processing": row[1],
        "sent": row[2],
        "failed": row[3],
        "staleProcessing": row[4],
        "healthy": row[3] == 0 and row[4] == 0,
    }
