from fastapi.testclient import TestClient

from api.production.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "eyt-erp",
        "version": "0.9.0",
    }


def test_ready_without_database_url() -> None:
    # The readiness endpoint must fail closed when DATABASE_URL is absent.
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "DATABASE_URL is not configured"
