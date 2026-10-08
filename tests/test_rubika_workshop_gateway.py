import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.rubika_workshop_gateway import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_webhook_persists_event(monkeypatch):
    monkeypatch.setenv("RUBIKA_WORKSHOP_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")

    stored = []

    def fake_persist(event, payload):
        stored.append((event, payload))
        return True

    monkeypatch.setattr(
        "api.rubika_workshop_gateway._persist_event",
        fake_persist,
    )

    payload = {
        "message": {
            "message_id": "m-100",
            "chat_id": "workshop-1",
            "text": "بوش X33 تعداد 3000 عدد تولید شد",
            "sender": {"user_id": "u-1", "name": "احسان"},
        }
    }

    response = _client().post(
        "/api/v1/integrations/rubika/workshop/webhook",
        params={"secret": "test-secret"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stored"] is True
    assert body["duplicate"] is False
    assert body["event"]["external_message_id"] == "m-100"
    assert body["event"]["message_type"] == "PRODUCTION"
    assert stored[0][1] == payload


def test_webhook_reports_duplicate(monkeypatch):
    monkeypatch.setenv("RUBIKA_WORKSHOP_WEBHOOK_SECRET", "test-secret")

    monkeypatch.setattr(
        "api.rubika_workshop_gateway._persist_event",
        lambda event, payload: False,
    )

    response = _client().post(
        "/api/v1/integrations/rubika/workshop/webhook",
        params={"secret": "test-secret"},
        json={"message": {"message_id": "m-101", "text": "پرداخت 500000 تومان"}},
    )

    assert response.status_code == 200
    assert response.json()["duplicate"] is True


def test_webhook_rejects_invalid_secret(monkeypatch):
    monkeypatch.setenv("RUBIKA_WORKSHOP_WEBHOOK_SECRET", "test-secret")

    response = _client().post(
        "/api/v1/integrations/rubika/workshop/webhook",
        params={"secret": "wrong"},
        json={"message": {"message_id": "m-102", "text": "سلام"}},
    )

    assert response.status_code == 401


def test_webhook_rejects_invalid_json(monkeypatch):
    monkeypatch.setenv("RUBIKA_WORKSHOP_WEBHOOK_SECRET", "test-secret")

    response = _client().post(
        "/api/v1/integrations/rubika/workshop/webhook",
        params={"secret": "test-secret"},
        content=b"not-json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
