from decimal import Decimal
from types import SimpleNamespace

from api.orders.postgres_adapter import PostgresInventoryGateway


def test_inventory_reservation_uses_physical_minus_reserved_stock():
    class Cursor:
        def __init__(self):
            self.calls = []
            self.rows = [("MAIN",), (Decimal("100"),), (Decimal("20"),)]

        def execute(self, sql, params=None):
            self.calls.append((sql, params))

        def fetchone(self):
            return self.rows.pop(0)

    cur = Cursor()
    item = SimpleNamespace(product_id="p1", quantity=Decimal("30"))
    PostgresInventoryGateway.reserve_in_transaction(cur, "MAIN", (item,), "EYT-TEST")

    assert len(cur.calls) == 3
    assert "FOR UPDATE" in cur.calls[0][0]
    assert "inventory_transactions" in cur.calls[1][0]
    assert "inventory_reservations" in cur.calls[2][0]
    assert cur.calls[2][1][0] == "EYT-TEST"


def test_inventory_reservation_rejects_insufficient_available_stock():
    class Cursor:
        def __init__(self):
            self.rows = [("MAIN",), (Decimal("100"),), (Decimal("80"),)]

        def execute(self, sql, params=None):
            pass

        def fetchone(self):
            return self.rows.pop(0)

    cur = Cursor()
    item = SimpleNamespace(product_id="p1", quantity=Decimal("30"))

    try:
        PostgresInventoryGateway.reserve_in_transaction(cur, "MAIN", (item,), "EYT-TEST")
    except ValueError as exc:
        assert "insufficient stock" in str(exc)
    else:
        raise AssertionError("reservation must fail when available stock is insufficient")
