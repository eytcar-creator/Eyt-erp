from decimal import Decimal

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.orders import fastapi_router


CUSTOMER_ID = "2b15dbb4-c1a9-4d3e-9f1a-39c1a0f6b122"
OTHER_CUSTOMER_ID = "3b15dbb4-c1a9-4d3e-9f1a-39c1a0f6b123"
PRODUCT_ID = "2a15dbb4-c1a9-4d3e-9f1a-39c1a0f6b121"


def _request():
    return Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/orders",
        "raw_path": b"/api/v1/orders",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 123),
    })


class _OrderCenter:
    def __init__(self):
        self.command = None

    def create(self, command):
        self.command = command
        return {"orderNo": "EYT-TEST-001", "status": "PENDING_CONFIRMATION"}


def _payload(customer_id=CUSTOMER_ID):
    return fastapi_router.OrderIn(
        customer_id=customer_id,
        warehouse_code="MAIN",
        channel="WEBSITE",
        items=[{
            "product_id": PRODUCT_ID,
            "quantity": Decimal("2"),
            "unit_price": Decimal("0.01"),
        }],
    )


def test_website_order_rejects_customer_id_not_bound_to_session(monkeypatch):
    center = _OrderCenter()
    monkeypatch.setattr(fastapi_router, "order_center", center)
    monkeypatch.setattr(
        fastapi_router,
        "require_customer_session",
        lambda _request: {"customerId": OTHER_CUSTOMER_ID},
    )
    resolver_called = False

    def resolver(*args, **kwargs):
        nonlocal resolver_called
        resolver_called = True
        return args[0]

    monkeypatch.setattr(fastapi_router, "_resolve_prices", resolver)

    with pytest.raises(HTTPException) as exc:
        fastapi_router.create_order(_payload(), _request())

    assert exc.value.status_code == 403
    assert resolver_called is False
    assert center.command is None


def test_website_order_passes_server_resolved_price_to_order_center(monkeypatch):
    center = _OrderCenter()
    monkeypatch.setattr(fastapi_router, "order_center", center)
    monkeypatch.setattr(
        fastapi_router,
        "require_customer_session",
        lambda _request: {"customerId": CUSTOMER_ID},
    )

    def resolver(items, customer_id=None):
        assert customer_id == CUSTOMER_ID
        return [items[0].model_copy(update={"unit_price": Decimal("87.50")})]

    monkeypatch.setattr(fastapi_router, "_resolve_prices", resolver)
    result = fastapi_router.create_order(_payload(), _request())

    assert result["orderNo"] == "EYT-TEST-001"
    assert center.command is not None
    assert center.command.customer_id == CUSTOMER_ID
    assert center.command.items[0].unit_price == Decimal("87.50")
    assert center.command.items[0].unit_price != Decimal("0.01")



def test_internal_channel_order_rejects_missing_or_invalid_token(monkeypatch):
    center = _OrderCenter()
    monkeypatch.setattr(fastapi_router, "order_center", center)
    monkeypatch.setenv("EYT_ERP_CHANNEL_TOKEN", "trusted-ingestion-secret")
    monkeypatch.setattr(
        fastapi_router,
        "_resolve_prices",
        lambda *args, **kwargs: pytest.fail("pricing must not run before channel authentication"),
    )
    payload = _payload()
    payload = payload.model_copy(update={"channel": fastapi_router.OrderChannel.SHOP})

    with pytest.raises(HTTPException) as missing:
        fastapi_router.create_order(payload, _request())
    assert missing.value.status_code == 401

    with pytest.raises(HTTPException) as invalid:
        fastapi_router.create_order(payload, _request(), channel_token="attacker-controlled")
    assert invalid.value.status_code == 401
    assert center.command is None


def test_internal_channel_order_accepts_configured_token(monkeypatch):
    center = _OrderCenter()
    monkeypatch.setattr(fastapi_router, "order_center", center)
    monkeypatch.setenv("EYT_ERP_CHANNEL_TOKEN", "trusted-ingestion-secret")
    monkeypatch.setattr(
        fastapi_router,
        "_resolve_prices",
        lambda items, customer_id=None: [
            items[0].model_copy(update={"unit_price": Decimal("87.50")})
        ],
    )
    payload = _payload()
    payload = payload.model_copy(update={"channel": fastapi_router.OrderChannel.SHOP})

    fastapi_router.create_order(
        payload, _request(), channel_token="trusted-ingestion-secret"
    )

    assert center.command is not None
    assert center.command.channel == fastapi_router.OrderChannel.SHOP



def test_internal_order_read_and_confirmation_access_requires_channel_token(monkeypatch):
    order = {
        "order_no": "EYT-TEST-002",
        "customer_id": CUSTOMER_ID,
        "channel": fastapi_router.OrderChannel.SHOP.value,
    }
    monkeypatch.setenv("EYT_ERP_CHANNEL_TOKEN", "trusted-ingestion-secret")

    with pytest.raises(HTTPException) as missing:
        fastapi_router._authorize_order_access(_request(), order, None)
    assert missing.value.status_code == 401

    with pytest.raises(HTTPException) as invalid:
        fastapi_router._authorize_order_access(_request(), order, "wrong-token")
    assert invalid.value.status_code == 401

    fastapi_router._authorize_order_access(
        _request(), order, "trusted-ingestion-secret"
    )


def test_website_order_access_remains_bound_to_customer_session(monkeypatch):
    order = {
        "order_no": "EYT-TEST-003",
        "customer_id": CUSTOMER_ID,
        "channel": fastapi_router.OrderChannel.WEBSITE.value,
    }
    monkeypatch.setattr(
        fastapi_router,
        "require_customer_session",
        lambda _request: {"customerId": OTHER_CUSTOMER_ID},
    )

    with pytest.raises(HTTPException) as exc:
        fastapi_router._authorize_order_access(_request(), order, None)
    assert exc.value.status_code == 403
