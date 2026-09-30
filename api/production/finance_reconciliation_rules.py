from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconciliationResult:
    status: str
    issues: tuple[str, ...]


def evaluate_reconciliation(
    customer_receivable,
    customer_collected,
    production_payable,
    production_paid,
    active_funding_balance,
) -> ReconciliationResult:
    issues: list[str] = []

    if customer_collected > customer_receivable:
        issues.append("customer_collected_exceeds_receivable")
    if production_paid > production_payable:
        issues.append("production_paid_exceeds_payable")
    if active_funding_balance < 0:
        issues.append("active_funding_balance_negative")

    return ReconciliationResult(
        status="ALERT" if issues else "OK",
        issues=tuple(issues),
    )
