from decimal import Decimal
from uuid import UUID

import pytest

from api.orders import fastapi_router


PRODUCT_ID = "2a15dbb4-c1a9-4d3e-9f1a-39c1a0f6b121"


class _Cursor:
    def __init__(self, customer_prices=(), master_prices=(), sale_price=Decimal("150")):
        self.customer_prices = list(customer_prices)
        self.master_prices = list(master_prices)
        self.sale_price = sale_price
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        if "SELECT id, sale_price, is_active FROM products" in sql:
            self.rows = [(UUID(PRODUCT_ID), self.sale_price, True)]
        elif "WITH requested(product_id, quantity)" in sql:
            self.rows = self.customer_prices
        elif "FROM price_master" in sql:
            self.rows = self.master_prices
        else:
            raise AssertionError(f"Unexpected pricing query: {sql}")

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self._cursor


def _patch_db(monkeypatch, cursor):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test.invalid/eyt")
    monkeypatch.setattr(
        fastapi_router.psycopg,
        "connect",
        lambda _url: _Connection(cursor),
    )


def test_customer_price_overrides_client_supplied_unit_price(monkeypatch):
    cursor = _Cursor(
        customer_prices=[(UUID(PRODUCT_ID), Decimal("87.50"))],
        sale_price=Decimal("150"),
    )
    _patch_db(monkeypatch, cursor)
    item = fastapi_router.ItemIn(
        product_id=PRODUCT_ID,
        quantity=Decimal("10"),
        unit_price=Decimal("1"),
    )

    resolved = fastapi_router._resolve_prices([item], customer_id="2b15dbb4-c1a9-4d3e-9f1a-39c1a0f6b122")

    assert resolved[0].unit_price == Decimal("87.50")


def test_price_master_overrides_client_supplied_unit_price(monkeypatch):
    cursor = _Cursor(
        master_prices=[(UUID(PRODUCT_ID), Decimal("112.25"))],
        sale_price=Decimal("150"),
    )
    _patch_db(monkeypatch, cursor)
    item = fastapi_router.ItemIn(
        product_id=PRODUCT_ID,
        quantity=Decimal("2"),
        unit_price=Decimal("0.01"),
    )

    resolved = fastapi_router._resolve_prices([item])

    assert resolved[0].unit_price == Decimal("112.25")


def test_missing_positive_server_price_is_rejected(monkeypatch):
    cursor = _Cursor(sale_price=Decimal("0"))
    _patch_db(monkeypatch, cursor)
    item = fastapi_router.ItemIn(
        product_id=PRODUCT_ID,
        quantity=Decimal("1"),
        unit_price=Decimal("0.01"),
    )

    with pytest.raises(Exception, match="product has no valid sale price"):
        fastapi_router._resolve_prices([item])
