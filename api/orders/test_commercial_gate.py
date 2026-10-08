from decimal import Decimal

from api.orders.commercial_gate import CommercialGate


def test_cash_gate_passes_when_stock_is_available():
    class Cursor:
        def __init__(self):
            self.calls = 0
        def execute(self, sql, params=()):
            self.calls += 1
            self.sql = sql
        def fetchone(self):
            # customer, warehouse, then product, then stock, reserved
            sequence = [
                ("c1", "Customer", True),
                ("MAIN",),
                ("p1", "P1", "3K000", "SKU", "بوش طبق", 100, 40, True),
                ("unused-master",),
                (50,),
                (0,),
            ]
            return sequence[min(self.calls - 1, len(sequence) - 1)]
        def fetchall(self):
            return []
    class Conn:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def cursor(self):
            return Cursor()
    gate = CommercialGate(lambda: Conn())
    result = gate.evaluate(
        customer_id="c1",
        warehouse_code="MAIN",
        payment_type="CASH",
        items=(
            type("Line", (), {"product_id": "p1", "quantity": Decimal("20")})(),
        ),
    )
    assert result["gate_status"] == "PASS"
    assert result["ready_for_confirmation"] is True
    assert result["mutations_performed"] is False
    assert result["items"][0]["available_stock"] == "50"
