from decimal import Decimal
from api.production.commercial_api import OrderLine, total

def test_order_total():
    lines = [OrderLine(sku="EYT-001", name="Test", qty=Decimal("2"), unitPrice=Decimal("100"), discount=Decimal("10"))]
    assert total(lines) == Decimal("190")
