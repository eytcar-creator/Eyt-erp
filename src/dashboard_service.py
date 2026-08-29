"""E.Y.T Management Dashboard snapshot v1."""
from decimal import Decimal

def build_management_snapshot(invoices, stocks, agencies):
    sales = sum((i.total for i in invoices), Decimal("0"))
    paid = sum((i.paid_amount for i in invoices), Decimal("0"))
    receivables = sum((i.balance for i in invoices), Decimal("0"))
    return {
        "sales": sales,
        "paid": paid,
        "receivables": receivables,
        "low_stock_skus": [s.sku for s in stocks if s.needs_reorder],
        "agency_scores": {a.code: a.score for a in agencies},
    }
