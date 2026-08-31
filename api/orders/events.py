from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(frozen=True)
class OrderEvent:
    event_type: str
    order_no: str
    occurred_at: str
    source: str = "EYT_ORDER_CENTER"
    version: int = 1

    def payload(self, **data: Any) -> dict[str, Any]:
        body = asdict(self)
        body["data"] = data
        return body


def order_confirmed_event(order_no: str, customer_id: str, representative_id: str | None) -> dict[str, Any]:
    return OrderEvent(
        event_type="order.confirmed",
        order_no=order_no,
        occurred_at=datetime.now(timezone.utc).isoformat(),
    ).payload(customer_id=customer_id, representative_id=representative_id)


def publish_event(event: dict[str, Any], publisher: Callable[[dict[str, Any]], None]) -> None:
    """Publish an already-committed domain event to the automation adapter."""
    publisher(event)
