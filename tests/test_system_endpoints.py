import pytest
from fastapi import HTTPException

from api.production.main import health, readiness


def test_health_endpoint() -> None:
    assert health() == {
        "status": "ok",
        "service": "eyt-erp",
        "version": "0.9.1",
    }


def test_ready_without_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    # The readiness endpoint must fail closed when DATABASE_URL is absent.
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        readiness()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "DATABASE_URL is not configured"
