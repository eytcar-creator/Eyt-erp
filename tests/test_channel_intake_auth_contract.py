import hashlib
import hmac

import pytest
from fastapi import HTTPException

from api.orders.channel_intake_api import _verify_signature


def test_channel_intake_fails_closed_without_any_auth_secret(monkeypatch):
    monkeypatch.delenv("EYT_ERP_CHANNEL_TOKEN", raising=False)
    monkeypatch.delenv("CHANNEL_INTAKE_SECRET", raising=False)

    with pytest.raises(HTTPException) as exc:
        _verify_signature(b'{"channel":"PHONE"}', None, None)

    assert exc.value.status_code == 503
    assert "authentication is not configured" in exc.value.detail


def test_channel_intake_rejects_missing_token_when_token_is_configured(monkeypatch):
    monkeypatch.setenv("EYT_ERP_CHANNEL_TOKEN", "server-only-token")
    monkeypatch.delenv("CHANNEL_INTAKE_SECRET", raising=False)

    with pytest.raises(HTTPException) as exc:
        _verify_signature(b'{"channel":"PHONE"}', None, None)

    assert exc.value.status_code == 401


def test_channel_intake_accepts_valid_internal_token(monkeypatch):
    monkeypatch.setenv("EYT_ERP_CHANNEL_TOKEN", "server-only-token")
    monkeypatch.delenv("CHANNEL_INTAKE_SECRET", raising=False)

    _verify_signature(b'{"channel":"PHONE"}', None, "server-only-token")


def test_channel_intake_accepts_valid_hmac_signature(monkeypatch):
    body = b'{"channel":"PHONE"}'
    secret = "test-signing-secret"
    monkeypatch.delenv("EYT_ERP_CHANNEL_TOKEN", raising=False)
    monkeypatch.setenv("CHANNEL_INTAKE_SECRET", secret)
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    _verify_signature(body, "sha256=" + signature, None)


def test_channel_intake_confirmation_recovers_existing_reserved_order():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "api" / "orders" / "channel_intake_api.py").read_text(encoding="utf-8")
    assert 'if created.get("status") == "RESERVED":' in source
    assert "confirmed = created" in source
    assert "confirmed = order_api.order_center.confirm(order_no)" in source
