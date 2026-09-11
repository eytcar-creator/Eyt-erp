"""Static contract/security tests for the E.Y.T customer portal.

These tests intentionally avoid a live PostgreSQL dependency. They protect the
security boundaries that must remain true when the database-backed integration
suite runs in CI/deployment.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "api/production/customer_portal_api.py").read_text(encoding="utf-8")
ORDERS = (ROOT / "api/orders/fastapi_router.py").read_text(encoding="utf-8")
MIGRATION = (ROOT / "database/migrations/020_customer_price_list_contract.sql").read_text(encoding="utf-8")


def test_customer_prices_never_accepts_customer_id():
    start = PORTAL.index('def customer_prices')
    end = PORTAL.index('@router.get("/orders")', start)
    block = PORTAL[start:end]
    assert "customer_id" not in block
    assert 'session["customerId"]' in block


def test_customer_order_is_tenant_scoped():
    start = PORTAL.index('@router.get("/orders/{order_no}")')
    block = PORTAL[start:]
    assert "WHERE order_no=%s AND customer_id=%s" in block
    assert '(order_no, session["customerId"])' in block


def test_customer_prices_require_authenticated_session():
    start = PORTAL.index('def customer_prices')
    end = PORTAL.index('@router.get("/orders")', start)
    block = PORTAL[start:end]
    assert "require_customer_session(request)" in block


def test_price_list_has_customer_foreign_key():
    assert "FOREIGN KEY (default_price_list_id) REFERENCES price_lists(id)" in MIGRATION


def test_price_resolution_is_server_side_for_website_and_b2b():
    assert 'payload.channel.value in {"WEBSITE", "B2B"}' in ORDERS
    assert "require_customer_session(request)" in ORDERS
    assert "_resolve_prices(items, customer_id=customer_id)" in ORDERS


def test_price_resolution_rejects_missing_or_invalid_price_without_client_override():
    assert "unit_price" in ORDERS
    assert "price_master" in ORDERS


def test_customer_password_is_bcrypt_checked():
    assert "bcrypt.checkpw" in PORTAL
    assert "password_hash" in PORTAL


def test_session_tokens_are_hashed_before_storage_lookup():
    assert "_hash_token(token)" in PORTAL
    assert "token_hash" in PORTAL


def test_logout_revokes_session():
    assert "revoked_at=CURRENT_TIMESTAMP" in PORTAL


def test_price_api_limits_results():
    start = PORTAL.index('def customer_prices')
    end = PORTAL.index('@router.get("/orders")', start)
    block = PORTAL[start:end]
    assert "min(500)" in block
    assert "LIMIT %s" in block
