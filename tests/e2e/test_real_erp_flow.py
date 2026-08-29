import os
import psycopg
from fastapi.testclient import TestClient
from api.production.main import app


def test_real_auth_product_inventory_production_and_audit_flow():
    client = TestClient(app)
    common = {"X-Correlation-ID": "ci-real-e2e"}
    bootstrap = client.post("/api/auth/bootstrap", headers={**common, "X-Bootstrap-Secret": os.environ["BOOTSTRAP_SECRET"]}, json={"username":"ci_ceo","password":"CI-test-password-1234","email":"ci@example.test"})
    assert bootstrap.status_code == 201, bootstrap.text
    login = client.post("/api/auth/login", headers=common, json={"username":"ci_ceo","password":"CI-test-password-1234"})
    assert login.status_code == 200, login.text
    tokens = login.json()
    auth = {**common, "Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get("/api/auth/me", headers=auth)
    assert me.status_code == 200
    assert "production.execute" in me.json()["permissions"]
    assert "product.write" in me.json()["permissions"]
    assert "inventory.execute" in me.json()["permissions"]

    product = client.post("/api/products", headers=auth, json={
        "sku":"EYT-E2E-001","productCode":"EYT-E2E-001","nameFa":"قطعه تست E.Y.T",
        "categoryCode":"STEERING_BALL_JOINT","barcode":"290000000001","reorderPoint":20,
        "minStock":10,"maxStock":100,
    })
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    detail = client.get("/api/products/EYT-E2E-001", headers=auth)
    assert detail.status_code == 200 and detail.json()["sku"] == "EYT-E2E-001"

    received = client.post("/api/inventory/transactions", headers=auth, json={
        "productCode":"EYT-E2E-001","warehouseCode":"MAIN","quantity":100,
        "transactionType":"RECEIPT","referenceType":"E2E","referenceId":"CI-RECEIPT-001","unitCost":150000,
    })
    assert received.status_code == 201, received.text
    balance = client.get("/api/inventory/balance/EYT-E2E-001/MAIN", headers=auth)
    assert balance.status_code == 200
    assert str(balance.json()["onHand"]) == "100"
    reservation = client.post("/api/inventory/reservations", headers=auth, json={
        "productCode":"EYT-E2E-001","warehouseCode":"MAIN","referenceType":"SALES_ORDER","referenceId":"SO-E2E-001","quantity":20,
    })
    assert reservation.status_code == 201, reservation.text
    assert str(client.get("/api/inventory/balance/EYT-E2E-001/MAIN", headers=auth).json()["available"]) == "80"
    assert client.post(f"/api/inventory/reservations/{reservation.json()['id']}/release", headers=auth).status_code == 200

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
        product_row = conn.execute("SELECT id FROM products WHERE product_code=%s", ("EYT-E2E-001",)).fetchone()
    assert str(product_row[0]) == str(product_id)
    assert tuple(map(str, row[:4])) == ("100.000","95.000","3.000","2.000")
    assert row[4] == "completed"
    assert audits >= 4
    refreshed = client.post("/api/auth/refresh", headers=common, json={"refresh_token":tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]
    assert client.post("/api/auth/logout", headers=auth, json={"refresh_token":new_refresh}).status_code == 200
    assert client.post("/api/auth/refresh", headers=common, json={"refresh_token":new_refresh}).status_code == 401
