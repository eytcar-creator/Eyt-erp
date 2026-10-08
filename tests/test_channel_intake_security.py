import hashlib
import hmac

from api.orders.channel_intake_api import _verify_signature


def test_internal_channel_token(monkeypatch):
    monkeypatch.setenv("EYT_ERP_CHANNEL_TOKEN", "internal-secret")
    _verify_signature(b"payload", None, "internal-secret")


def test_hmac_channel_signature(monkeypatch):
    monkeypatch.setenv("EYT_ERP_CHANNEL_TOKEN", "")
    monkeypatch.setenv("CHANNEL_INTAKE_SECRET", "hmac-secret")
    signature = hmac.new(b"hmac-secret", b"payload", hashlib.sha256).hexdigest()
    _verify_signature(b"payload", f"sha256={signature}")
