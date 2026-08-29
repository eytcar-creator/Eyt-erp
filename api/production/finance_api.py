from decimal import Decimal
from typing import Any


def calculate_receivable(invoice_total: Decimal, collected: Decimal) -> Decimal:
    if invoice_total < 0 or collected < 0:
        raise ValueError("Amounts cannot be negative")
    return max(Decimal("0"), invoice_total - collected)


def calculate_cash_cycle_days(material_date: Any, sale_date: Any, collection_date: Any) -> int:
    return (collection_date - material_date).days
