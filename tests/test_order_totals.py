from decimal import Decimal

from api.orders.order_center import CreateOrder, OrderChannel, OrderLine, PaymentType
from api.orders.postgres_adapter import PostgresOrderRepository


class _Cursor:
    def __init__(self):
        self.executed = []
        self._row = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if "INSERT INTO sales_orders" in sql:
            self._row = (
                "sales-order-uuid",
                params[0],
                params[1],
                params[2],
                params[3],
                params[4],
                "PENDING_CONFIRMATION",
                params[8],
            )

    def fetchone(self):
        row, self._row = self._row, None
        return row


class _Connection:
    def __init__(self):
        self.cur = _Cursor()
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_order_creation_persists_subtotal_total_and_line_total():
    connection = _Connection()
    repo = PostgresOrderRepository(lambda: connection)
    repo._new_order_no = lambda: "EYT-TEST-TOTALS"
    command = CreateOrder(
        customer_id="customer-uuid",
        warehouse_code="MAIN",
        channel=OrderChannel.WEBSITE,
        items=(
            OrderLine(
                product_id="product-uuid-1",
                quantity=Decimal("2"),
                unit_price=Decimal("87.50"),
            ),
            OrderLine(
                product_id="product-uuid-2",
                quantity=Decimal("3"),
                unit_price=Decimal("12.25"),
            ),
        ),
        payment_type=PaymentType.CASH,
    )

    result = repo.create(command)

    subtotal = Decimal("211.75")
    order_insert = next(x for x in connection.cur.executed if "INSERT INTO sales_orders" in x[0])
    item_inserts = [x for x in connection.cur.executed if "INSERT INTO sales_order_items" in x[0]]
    assert "subtotal, total_amount" in order_insert[0]
    assert order_insert[1][-2:] == (subtotal, subtotal)
    assert len(item_inserts) == 2
    assert item_inserts[0][1][-1] == Decimal("175.00")
    assert item_inserts[1][1][-1] == Decimal("36.75")
    assert result["order_no"] == "EYT-TEST-TOTALS"
    assert connection.committed is True
    assert connection.rolled_back is False
