from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeliveryResult:
    accepted: bool
    provider: str
    channel: str
    provider_message_id: str | None = None
    error: str | None = None


class NotificationProvider:
    """Provider-neutral contract. No external delivery is performed here."""

    name = "UNCONFIGURED"

    def send(self, *, channel: str, payload: dict[str, Any]) -> DeliveryResult:
        raise NotImplementedError


class DryRunNotificationProvider(NotificationProvider):
    """Safe deployment/test adapter. It never contacts an external service."""

    name = "DRY_RUN"

    def send(self, *, channel: str, payload: dict[str, Any]) -> DeliveryResult:
        return DeliveryResult(
            accepted=False,
            provider=self.name,
            channel=channel,
            error="DRY_RUN provider does not deliver external notifications",
        )


def get_notification_provider() -> NotificationProvider:
    provider = "DRY_RUN"
    return DryRunNotificationProvider()
