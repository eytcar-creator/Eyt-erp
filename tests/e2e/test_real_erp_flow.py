import os
import psycopg
from fastapi.testclient import TestClient
from api.production.main import app


def test_real_auth_production_and_audit_flow():
    client = TestClient(app)
    common = {"X-Correlation-ID": "ci-real-e2e"}
    bootstrap = client.post("/api/auth/bootstrap", headers={**common, "X-Bootstrap-Secret": os.environ["BOOTSTRAP_SECRET"]}, json={"username":"ci_ceo","password":"CI-test-password-1234","email":"ci@example.test"})
    assert bootstrap.status_code == 201, bootstrap.text
    login = client.post("/api/auth/login", headers=common, json={"username":"ci_ceo","password":"CI-test-password-1234"})
    assert login.status_code == 200, login.text
    tokens = login.json()
    auth = {**common, "Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get("/api/auth/me", headers=auth)
    assert me.status_code == 200 and "production.execute" in me.json()["permissions"]
    assert client.get("/api/production/orders/CI-E2E-001", headers=common).status_code == 401
    order = client.post("/api/production/orders", headers=auth, json={"orderNo":"CI-E2E-001","productCode":"EYT-E2E-001","productName":"Synthetic E.Y.T Test Part","targetQty":100,"orderDate":"2026-08-29"})
    assert order.status_code == 201, order.text
    assert client.get("/api/production/orders/CI-E2E-001", headers=auth).json()["status"] == "planned"
    started = client.post("/api/production/orders/CI-E2E-001/operations/FORGE/start", headers=auth, json={"sequenceNo":1,"operationCode":"FORGE","operationName":"Forging","contractorName":"Synthetic Contractor"})
    assert started.status_code == 200, started.text
    completed = client.post("/api/production/orders/CI-E2E-001/operations/FORGE/complete", headers=auth, json={"sequenceNo":1,"operationCode":"FORGE","operationName":"Forging","inputQty":100,"acceptedQty":95,"rejectedQty":3,"wasteQty":2,"serviceCost":150000,"transportCost":25000,"contractorName":"Synthetic Contractor"})
    assert completed.status_code == 200, completed.text
    invalid = client.post("/api/production/orders/CI-E2E-001/operations/FORGE/complete", headers=auth, json={"sequenceNo":1,"operationCode":"FORGE","operationName":"Forging","inputQty":100,"acceptedQty":96,"rejectedQty":3,"wasteQty":2})
    assert invalid.status_code == 409
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute("SELECT input_qty,accepted_qty,rejected_qty,waste_qty,status FROM production_operations WHERE production_order_id=(SELECT id FROM production_orders WHERE order_no=%s) AND operation_code=%s", ("CI-E2E-001","FORGE")).fetchone()
        audits = conn.execute("SELECT count(*) FROM eyt_audit_logs WHERE actor_user_id=(SELECT id FROM eyt_users WHERE username=%s)", ("ci_ceo",)).fetchone()[0]
    assert tuple(map(str, row[:4])) == ("100.000","95.000","3.000","2.000")
    assert row[4] == "completed"
    assert audits >= 3
    refreshed = client.post("/api/auth/refresh", headers=common, json={"refresh_token":tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]
    assert client.post("/api/auth/logout", headers=auth, json={"refresh_token":new_refresh}).status_code == 200
    assert client.post("/api/auth/refresh", headers=common, json={"refresh_token":new_refresh}).status_code == 401
