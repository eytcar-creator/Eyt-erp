from __future__ import annotations

import logging
import os
import socket

from .finance_notification_dispatcher import dispatch_event
from .finance_notification_health import queue_health
from .finance_notification_result import mark_failed, mark_sent
from .finance_notification_worker_contract import claim_batch, reclaim_stale_events

logger = logging.getLogger(__name__)


def run_once(worker_id: str | None = None, limit: int = 25) -> dict:
    """Process one bounded notification queue batch.

    The worker owns notification state only. Financial ledger tables are not
    modified by this module.
    """
    worker_id = worker_id or os.getenv("FINANCE_NOTIFICATION_WORKER_ID") or socket.gethostname()
    reclaimed = reclaim_stale_events()
    events = claim_batch(worker_id, limit=limit)
    sent = 0
    failed = 0

    for event in events:
        try:
            result = dispatch_event(
                event_id=event.id,
                event_type=event.event_type,
                payload=event.payload,
            )
            if result.accepted:
                if mark_sent(event.id, worker_id):
                    sent += 1
            else:
                if mark_failed(event.id, worker_id, result.error or "provider rejected delivery"):
                    failed += 1
        except Exception as exc:
            logger.exception("notification event %s failed", event.id)
            if mark_failed(event.id, worker_id, str(exc)):
                failed += 1

    health = queue_health()
    return {
        "workerId": worker_id,
        "reclaimed": reclaimed,
        "claimed": len(events),
        "sent": sent,
        "failed": failed,
        "health": health,
    }
