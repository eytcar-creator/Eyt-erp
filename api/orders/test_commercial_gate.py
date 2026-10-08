from decimal import Decimal

from api.orders.commercial_gate import CommercialGate


def test_cash_gate_passes_when_stock_is_available():
    class Cursor:
        def __init__(self):
            self.last_sql = ""

        def execute(self, sql, params=()):
            self.last_sql = sql

        def fetchone(self):
            if "FROM customers" in self.last_sql:
                return ("c1", "Customer", True)
            if "FROM warehouses" in self.last_sql:
                return ("MAIN",)
            if "FROM inventory_transactions" in self.last_sql:
                return (50,)
            if "FROM inventory_reservations" in self.last_sql:
                return (0,)
            raise AssertionError(f"unexpected fetchone SQL: {self.last_sql}")

        def fetchall(self):
            if "FROM requested" in self.last_sql and "JOIN products" in self.last_sql:
                return [("p1", Decimal("20"), "3K000", "SKU", "بوش طبق", Decimal("100"), Decimal("40"), True)]
            if "FROM requested" in self.last_sql and "price_list_items" in self.last_sql:
                return []
            if "FROM price_master" in self.last_sql:
                return []
            raise AssertionError(f"unexpected fetchall SQL: {self.last_sql}")

    class Conn:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def cursor(self): return Cursor()

    gate = CommercialGate(lambda: Conn())
    result = gate.evaluate(
        customer_id="c1",
        warehouse_code="MAIN",
        payment_type="CASH",
        items=(type("Line", (), {"product_id": "p1", "quantity": Decimal("20")})(),),
    )

    assert result["gate_status"] == "PASS"
    assert result["ready_for_confirmation"] is True
    assert result["mutations_performed"] is False
    assert result["items"][0]["available_stock"] == "50"
