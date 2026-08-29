"""Production dashboard calculations for E.Y.T ERP."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class OperationSnapshot:
    code: str
    name: str
    status: str
    planned_end: object | None = None
    actual_end: object | None = None
    accepted_qty: Decimal = Decimal("0")
    rejected_qty: Decimal = Decimal("0")
    waste_qty: Decimal = Decimal("0")


def summarize_operations(operations: Iterable[OperationSnapshot]) -> dict[str, object]:
    ops = list(operations)
    total = len(ops)
    completed = sum(o.status == "completed" for o in ops)
    rejected = sum(o.status == "rejected" or o.rejected_qty > 0 for o in ops)
    waste = sum((o.waste_qty for o in ops), Decimal("0"))
    accepted = sum((o.accepted_qty for o in ops), Decimal("0"))
    return {
        "total_operations": total,
        "completed_operations": completed,
        "completion_percent": (Decimal(completed * 100) / Decimal(total)).quantize(Decimal("0.01")) if total else Decimal("0"),
        "operations_with_rejection": rejected,
        "accepted_qty": accepted,
        "waste_qty": waste,
    }
