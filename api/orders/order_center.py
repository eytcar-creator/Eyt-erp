from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol


class OrderChannel(str, Enum):
    WEBSITE = "WEBSITE"
    WHATSAPP = "WHATSAPP"
    PHONE = "PHONE"
    INSTAGRAM = "INSTAGRAM"
    SHOP = "SHOP"
    REPRESENTATIVE = "REPRESENTATIVE"
    OTHER = "OTHER"


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    RESERVED = "RESERVED"
    PREPARING = "PREPARING"
    READY_TO_SHIP = "READY_TO_SHIP"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


@dataclass(frozen=True)
class OrderLine:
    product_id: str
    quantity: Decimal
    unit_price: Decimal


@dataclass(frozen=True)
class CreateOrder:
    customer_id: str
    warehouse_code: str
    channel: OrderChannel
    items: tuple[OrderLine, ...]
    representative_id: str | None = None
    idempotency_key: str | None = None
    notes: str | None = None


class OrderRepository(Protocol):
    def create(self, order: CreateOrder) -> dict: ...
    def get(self, order_no: str) -> dict | None: ...
    def confirm(self, order_no: str) -> dict: ...


class InventoryGateway(Protocol):
    def reserve(self, warehouse_code: str, items: tuple[OrderLine, ...]) -> None: ...


class OrderCenter:
    """Application service. Persistence/HTTP adapters stay outside this domain layer."""

    def __init__(self, orders: OrderRepository, inventory: InventoryGateway):
        self.orders = orders
        self.inventory = inventory

    def create(self, command: CreateOrder) -> dict:
        if not command.items:
            raise ValueError("order must contain at least one item")
        for line in command.items:
            if line.quantity <= 0:
                raise ValueError("quantity must be positive")
            if line.unit_price < 0:
                raise ValueError("unit price cannot be negative")
        return self.orders.create(command)

    def confirm(self, order_no: str) -> dict:
        # The concrete PostgreSQL adapter must execute validation, reservation,
        # status transition and audit event in one database transaction.
        order = self.orders.get(order_no)
        if not order:
            raise KeyError(order_no)
        if order["status"] not in {
            OrderStatus.PENDING_CONFIRMATION.value,
            OrderStatus.CONFIRMED.value,
        }:
            raise ValueError("order is not confirmable")
        items = tuple(
            OrderLine(
                product_id=i["product_id"],
                quantity=Decimal(str(i["quantity"])),
                unit_price=Decimal(str(i["unit_price"])),
            )
            for i in order["items"]
        )
        self.inventory.reserve(order["warehouse_code"], items)
        return self.orders.confirm(order_no)
