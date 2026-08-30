import os
import psycopg
from fastapi.testclient import TestClient
from api.production.main import app


def test_real_end_to_end_business_flow():
    client = TestClient(app)
    common = {"X-Correlation-ID": "ci-real-e2e"}

    bootstrap = client.post(
        "/api/auth/bootstrap",
        headers={**common, "X-Bootstrap-Secret": os.environ["BOOTSTRAP_SECRET"]},
        json={"username": "ci_ceo", "password": "CI-test-password-1234", "email": "ci@example.test"},
    )
    assert bootstrap.status_code in (201, 409), bootstrap.text

    login = client.post(
        "/api/auth/login",
        headers=common,
        json={"username": "ci_ceo", "password": "CI-test-password-1234"},
    )
    if login.status_code != 200:
        login = client.post(
            "/api/auth/login",
            headers=common,
            json={"username": "ci_purchase", "password": "CI-test-password-1234"},
        )
    assert login.status_code == 200, login.text
    tokens = login.json()
    auth = {**common, "Authorization": f"Bearer {tokens['access_token']}"}

    me = client.get("/api/auth/me", headers=auth)
    assert me.status_code == 200
    permissions = set(me.json()["permissions"])
    assert {"production.execute", "product.write", "inventory.execute", "sales.write", "sales.fulfill", "finance.write", "qc.execute", "qc.release"}.issubset(permissions)

    customer = client.post(
        "/api/sales/customers",
        headers=auth,
        json={"customerCode": "CI-CUSTOMER-001", "name": "E.Y.T CI Customer", "phone": "0000000000", "creditLimit": 100000000},
    )
    assert customer.status_code in (201, 409), customer.text

    product = client.post(
        "/api/products",
        headers=auth,
        json={
            "sku": "EYT-E2E-001",
            "productCode": "EYT-E2E-001",
            "nameFa": "قطعه تست E.Y.T",
            "categoryCode": "STEERING_BALL_JOINT",
            "barcode": "290000000001",
            "reorderPoint": 20,
            "minStock": 10,
            "maxStock": 100,
        },
    )
    assert product.status_code in (201, 409), product.text
    detail = client.get("/api/products/EYT-E2E-001", headers=auth)
    assert detail.status_code == 200
    product_id = detail.json()["id"]

    received = client.post(
        "/api/inventory/transactions",
        headers=auth,
        json={
            "productCode": "EYT-E2E-001",
            "warehouseCode": "MAIN",
            "quantity": 100,
            "transactionType": "RECEIPT",
            "referenceType": "E2E",
            "referenceId": "CI-RECEIPT-001",
            "unitCost": 150000,
        },
    )
    assert received.status_code in (201, 409), received.text
    balance = client.get("/api/inventory/balance/EYT-E2E-001/MAIN", headers=auth)
    assert balance.status_code == 200
    assert balance.json()["onHand"] >= 100

    reservation = client.post(
        "/api/inventory/reservations",
        headers=auth,
        json={
            "productCode": "EYT-E2E-001",
            "warehouseCode": "MAIN",
            "referenceType": "SALES_ORDER",
            "referenceId": "SO-E2E-001",
            "quantity": 20,
        },
    )
    assert reservation.status_code in (201, 409), reservation.text
    if reservation.status_code == 201:
        assert client.post(f"/api/inventory/reservations/{reservation.json()['id']}/release", headers=auth).status_code == 200

    order = client.post(
        "/api/production/orders",
        headers=auth,
        json={"orderNo": "CI-E2E-001", "productCode": "EYT-E2E-001", "productName": "Synthetic E.Y.T Test Part", "targetQty": 100, "orderDate": "2026-08-30"},
    )
    assert order.status_code in (201, 409), order.text

    started = client.post(
        "/api/production/orders/CI-E2E-001/operations/FORGE/start",
        headers=auth,
        json={"sequenceNo": 1, "operationCode": "FORGE", "operationName": "Forging", "contractorName": "Synthetic Contractor"},
    )
    assert started.status_code in (200, 409), started.text

    completed = client.post(
        "/api/production/orders/CI-E2E-001/operations/FORGE/complete",
        headers=auth,
        json={"sequenceNo": 1, "operationCode": "FORGE", "operationName": "Forging", "inputQty": 100, "acceptedQty": 95, "rejectedQty": 3, "wasteQty": 2, "serviceCost": 150000, "transportCost": 25000, "contractorName": "Synthetic Contractor"},
    )
    assert completed.status_code in (200, 409), completed.text

    invalid = client.post(
        "/api/production/orders/CI-E2E-001/operations/FORGE/complete",
        headers=auth,
        json={"sequenceNo": 1, "operationCode": "FORGE", "operationName": "Forging", "inputQty": 100, "acceptedQty": 96, "rejectedQty": 3, "wasteQty": 2},
    )
    assert invalid.status_code == 409

    batch = client.post(
        "/api/qc/batches",
        headers=auth,
        json={"batch_no": "CI-BATCH-001", "production_order_no": "CI-E2E-001", "product_code": "EYT-E2E-001", "planned_qty": 95},
    )
    assert batch.status_code in (201, 409), batch.text

    inspection = client.post(
        "/api/qc/batches/CI-BATCH-001/inspect",
        headers=auth,
        json={"inspection_type": "FINAL", "result": "PASS", "inspector": "CI-QC", "accepted_qty": 95, "rejected_qty": 0, "notes": "Synthetic final acceptance"},
    )
    assert inspection.status_code in (200, 409), inspection.text

    release = client.post(
        "/api/qc/batches/CI-BATCH-001/release",
        headers=auth,
        json={"warehouse_code": "MAIN", "quantity": 20, "released_by": "CI-QC"},
    )
    assert release.status_code in (201, 409), release.text

    sales_order = client.post(
        "/api/sales/orders",
        headers=auth,
        json={"orderNo": "SO-E2E-001", "customerCode": "CI-CUSTOMER-001", "warehouseCode": "MAIN", "orderDate": "2026-08-30", "lines": [{"productCode": "EYT-E2E-001", "quantity": 20, "unitPrice": 250000}], "prepayment": 1000000},
    )
    assert sales_order.status_code in (201, 409), sales_order.text

    confirmed = client.post("/api/sales/orders/SO-E2E-001/confirm", headers=auth)
    assert confirmed.status_code in (200, 409), confirmed.text

    invoice = client.post("/api/sales/orders/SO-E2E-001/invoice", headers=auth, json={"invoiceNo": "INV-E2E-001"})
    assert invoice.status_code in (201, 409), invoice.text

    fulfilled = client.post("/api/sales/orders/SO-E2E-001/fulfill", headers=auth)
    assert fulfilled.status_code in (200, 409), fulfilled.text

    payment = client.post(
        "/api/sales/payments",
        headers=auth,
        json={"amount": 4000000, "paymentDate": "2026-08-30", "paymentMethod": "CI", "referenceNo": "CI-PAY-001", "invoiceNo": "INV-E2E-001"},
    )
    assert payment.status_code in (201, 409), payment.text

    sales_detail = client.get("/api/sales/orders/SO-E2E-001", headers=auth)
    assert sales_detail.status_code == 200
    assert sales_detail.json()["orderNo"] == "SO-E2E-001"

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        product_row = conn.execute("SELECT id FROM products WHERE product_code=%s", ("EYT-E2E-001",)).fetchone()
        operation = conn.execute("SELECT input_qty,accepted_qty,rejected_qty,waste_qty,status FROM production_operations WHERE production_order_id=(SELECT id FROM production_orders WHERE order_no=%s) AND operation_code=%s", ("CI-E2E-001", "FORGE")).fetchone()
        audits = conn.execute("SELECT count(*) FROM eyt_audit_logs WHERE actor_user_id=(SELECT id FROM eyt_users WHERE username=%s)", ("ci_purchase",)).fetchone()[0]
        invoice_row = conn.execute("SELECT status,receivable_amount FROM invoices WHERE invoice_no=%s", ("INV-E2E-001",)).fetchone()
        sales_row = conn.execute("SELECT status FROM sales_orders WHERE order_no=%s", ("SO-E2E-001",)).fetchone()
        release_row = conn.execute("SELECT release_status,quantity FROM finished_goods_releases WHERE quality_batch_id=(SELECT id FROM quality_batches WHERE batch_no=%s)", ("CI-BATCH-001",)).fetchone()

    assert str(product_row[0]) == str(product_id)
    assert operation is not None
    assert tuple(map(str, operation[:4])) == ("100.000", "95.000", "3.000", "2.000")
    assert operation[4] == "completed"
    assert audits >= 8
    assert invoice_row is not None and invoice_row[0] in ("PAID", "PARTIALLY_PAID")
    assert sales_row == ("FULFILLED",)
    assert release_row is not None and release_row[0] == "RELEASED"

    refreshed = client.post("/api/auth/refresh", headers=common, json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]
    assert client.post("/api/auth/logout", headers=auth, json={"refresh_token": new_refresh}).status_code == 200
    assert client.post("/api/auth/refresh", headers=common, json={"refresh_token": new_refresh}).status_code == 401
