"""HTTP adapter for the production service.

Framework-neutral handlers that can be mounted in FastAPI, Flask, or another
HTTP layer. Persistence is intentionally injected so business rules stay
separate from the database implementation.
"""
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from .production_service import OperationResult, ProductionOrder


class ProductionRepository:
    def __init__(self) -> None:
        self.orders: dict[str, ProductionOrder] = {}

    def save(self, order: ProductionOrder) -> ProductionOrder:
        self.orders[order.order_no] = order
        return order

    def get(self, order_no: str) -> ProductionOrder | None:
        return self.orders.get(order_no)


repository = ProductionRepository()


def create_order(payload: dict[str, Any]) -> dict[str, Any]:
    order = ProductionOrder(
        order_no=payload["orderNo"],
        product_code=payload["productCode"],
        product_name=payload["productName"],
        target_qty=Decimal(str(payload["targetQty"])),
        order_date=payload["orderDate"],
    )
    repository.save(order)
    return {"orderNo": order.order_no, "status": "planned"}


def complete_operation(order_no: str, operation_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    order = repository.get(order_no)
    if order is None:
        raise KeyError(f"Production order not found: {order_no}")
    operation = OperationResult(
        operation_code=operation_code,
        input_qty=Decimal(str(payload["inputQty"])),
        accepted_qty=Decimal(str(payload["acceptedQty"])),
        rejected_qty=Decimal(str(payload.get("rejectedQty", 0))),
        waste_qty=Decimal(str(payload.get("wasteQty", 0))),
        service_cost=Decimal(str(payload.get("serviceCost", 0))),
        transport_cost=Decimal(str(payload.get("transportCost", 0))),
    )
    order.add_operation(operation)
    return {"orderNo": order_no, "operation": asdict(operation), "status": "completed"}
