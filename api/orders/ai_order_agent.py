from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ProposedItem:
    product_code: str | None
    quantity: Decimal
    confidence: float


@dataclass(frozen=True)
class OrderProposal:
    customer_id: str | None
    items: tuple[ProposedItem, ...]
    payment_mode: str | None
    confidence: float
    missing: tuple[str, ...]
    needs_confirmation: bool = True


# Conservative parser: it proposes structure only. It never creates or confirms
# an order. Ambiguity is deliberately surfaced to the caller.
class AIOrderAgent:
    def propose(self, text: str, customer_id: str | None = None) -> dict[str, Any]:
        clean = " ".join((text or "").strip().split())
        missing: list[str] = []
        items: list[ProposedItem] = []

        # Supports common commercial formats such as:
        # "JAC S5 3K000 x 20", "3K000 20 عدد", "کد 3K000 تعداد 20"
        patterns = (
            r"(?P<code>[A-Za-z0-9][A-Za-z0-9._-]{2,})\s*(?:x|×|عدد|pcs|تعداد|quantity|qty)\s*(?P<qty>\d+(?:\.\d+)?)",
            r"(?:کد|sku|code)\s*[:#-]?\s*(?P<code>[A-Za-z0-9][A-Za-z0-9._-]{2,})\s*(?:تعداد|quantity|qty|x|×)\s*(?P<qty>\d+(?:\.\d+)?)",
        )
        for pattern in patterns:
            for m in re.finditer(pattern, clean, flags=re.IGNORECASE):
                code = m.group("code")
                qty = Decimal(m.group("qty"))
                if qty > 0:
                    items.append(ProposedItem(code, qty, 0.96))

        if not items:
            missing.append("items")
        if not customer_id:
            missing.append("customer")

        payment_mode = None
        if re.search(r"اعتباری|نسیه|credit", clean, re.I):
            payment_mode = "CREDIT"
        elif re.search(r"نقد|کارت|cash", clean, re.I):
            payment_mode = "CASH"

        confidence = 0.95 if items else 0.20
        if not customer_id:
            confidence = min(confidence, 0.70)

        return {
            "customer_id": customer_id,
            "items": [
                {"product_code": i.product_code, "quantity": str(i.quantity), "confidence": i.confidence}
                for i in items
            ],
            "payment_mode": payment_mode,
            "confidence": confidence,
            "missing": missing,
            "needs_confirmation": True,
            "next_action": "CONFIRM_CUSTOMER_AND_ITEMS" if not missing else "RESOLVE_MISSING_FIELDS",
        }
