from __future__ import annotations

import os
from typing import Any

from .finance_notification_provider import DeliveryResult, get_notification_provider


def channel_for_event(event_type: str) -> str:
    channels = {
        "FINANCE_SETTLEMENT_ALERT": os.getenv(
            "FINANCE_SETTLEMENT_ALERT_CHANNEL", "EMAIL"
        ).upper(),
    }
    return channels.get(event_type, "EMAIL")


def dispatch_event(
    *, event_id: int, event_type: str, payload: dict[str, Any]
) -> DeliveryResult:
    """Dispatch through the configured adapter.

    The default provider is DRY_RUN, so this function cannot send an
    external message until a real provider adapter is deliberately wired.
    """
    channel = channel_for_event(event_type)
    provider = get_notification_provider()
    return provider.send(channel=channel, payload=payload)
