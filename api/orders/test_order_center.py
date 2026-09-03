from decimal import Decimal

import pytest

from .order_center import CreateOrder, OrderChannel, OrderCenter, OrderLine, OrderStatus


class FakeOrders:
    def __init__(self, inventory):
        self.data = {}
        self.inventory = inventory

    def create(self, order):
        value = {"status": OrderStatus.PENDING_CONFIRMATION.value, "items": [
            {"product_id": x.product_id, "quantity": str(x.quantity), "unit_price": str(x.unit_price)}
            for x in order.items
        ], "warehouse_code": order.warehouse_code}
        self.data["EYT-ORD-TEST"] = value
        return {"order_no": "EYT-ORD-TEST", **value}

    def get(self, order_no):
        return self.data.get(order_no)

    def confirm(self, order_no):
        self.data[order_no]["status"] = OrderStatus.RESERVED.value
        return {"order_no": order_no, **self.data[order_no]}

    def confirm_with_controls(self, *, order_no, customer_id, warehouse_code, payment_type, items):
        self.inventory.reserve(warehouse_code, items)
        return self.confirm(order_no)


class FakeInventory:
    def __init__(self):
        self.calls = []

    def reserve(self, warehouse_code, items):
        self.calls.append((warehouse_code, items))


def service():
    inventory = FakeInventory()
    orders = FakeOrders(inventory)
    return OrderCenter(orders, inventory), orders, inventory


def test_create_rejects_empty_items():
    center, _, _ = service()
    with pytest.raises(ValueError):
        center.create(CreateOrder("c1", "WH1", OrderChannel.SHOP, ()))


def test_create_rejects_non_positive_quantity():
    center, _, _ = service()
    with pytest.raises(ValueError):
        center.create(CreateOrder("c1", "WH1", OrderChannel.SHOP, (
            OrderLine("p1", Decimal("0"), Decimal("10")),
        )))


def test_confirm_reserves_inventory_and_changes_state():
    center, _, inventory = service()
    created = center.create(CreateOrder("c1", "WH1", OrderChannel.SHOP, (
        OrderLine("p1", Decimal("2"), Decimal("10")),
    )))
    result = center.confirm(created["order_no"])
    assert result["status"] == OrderStatus.RESERVED.value
    assert len(inventory.calls) == 1
