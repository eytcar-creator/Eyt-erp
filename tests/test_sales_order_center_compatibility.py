from pathlib import Path

from api.production.sales_api import (
    FULFILLABLE_ORDER_STATUSES,
    INVOICEABLE_ORDER_STATUSES,
)


def test_order_center_reserved_status_is_supported_by_sales_routes():
    assert "RESERVED" in FULFILLABLE_ORDER_STATUSES
    assert "RESERVED" in INVOICEABLE_ORDER_STATUSES
    assert "CONFIRMED" in FULFILLABLE_ORDER_STATUSES
    assert "FULFILLED" in INVOICEABLE_ORDER_STATUSES


def test_fulfillment_excludes_its_own_reservation_and_consumes_it():
    source = Path("api/production/sales_api.py").read_text(encoding="utf-8")
    assert "AND NOT ((reference_type='SALES_ORDER' AND reference_id=%s) OR document_no=%s)" in source
    assert "SET status='CONSUMED'" in source
    assert "VALUES(%s,%s,%s,'PCS','ISSUE','SALES_ORDER',%s,%s)" in source
