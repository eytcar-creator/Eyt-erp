import os
from decimal import Decimal

from fastapi.testclient import TestClient

from api.production.main import app


def test_purchase_receiving_partial_full_and_inventory():
    client = TestClient(app)
    common = {"X-Correlation-ID": "ci-purchase-receiving"}
    bootstrap = client.post(
        "/api/auth/bootstrap",
        headers={**common, "X-Bootstrap-Secret": os.environ["BOOTSTRAP_SECRET"]},
        json={"username": "ci_purchase", "password": "CI-test-password-1234", "email": "ci-purchase@example.test"},
    )
    assert bootstrap.status_code in (201, 409), bootstrap.text
    login = client.post("/api/auth/login", headers=common, json={"username": "ci_purchase", "password": "CI-test-password-1234"})
    if login.status_code != 200:
        login = client.post("/api/auth/login", headers=common, json={"username": "ci_ceo", "password": "CI-test-password-1234"})
    assert login.status_code == 200, login.text
    auth = {**common, "Authorization": f"Bearer {login.json()['access_token']}"}

    product = client.post("/api/products", headers=auth, json={
        "sku": "EYT-PR-001", "productCode": "EYT-PR-001", "nameFa": "قطعه خرید تست E.Y.T",
        "categoryCode": "STEERING_BALL_JOINT", "purchasePrice": 125000,
    })
    assert product.status_code in (201, 409), product.text

    supplier = client.post("/api/purchase/suppliers", headers=auth, json={
        "supplierCode": "SUP-CI-001", "name": "Synthetic Supplier",
    })
    assert supplier.status_code in (201, 409), supplier.text
    supplier_id = supplier.json()["id"] if supplier.status_code == 201 else None
    if supplier_id is None:
        import psycopg
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            supplier_id = conn.execute("SELECT id FROM eyt_suppliers WHERE supplier_code='SUP-CI-001'").fetchone()[0]

    order = client.post("/api/purchase/orders", headers=auth, json={
        "orderNo": "PO-CI-001", "supplierId": str(supplier_id), "warehouseCode": "MAIN",
        "orderDate": "2026-08-29", "lines": [{"productCode": "EYT-PR-001", "quantity": 100, "unitPrice": 125000}],
    })
    assert order.status_code in (201, 409), order.text
    assert client.post("/api/purchase/orders/PO-CI-001/approve", headers=auth).status_code in (200, 409)

    first = client.post("/api/purchase/orders/PO-CI-001/receive", headers=auth, json={
        "receiptNo": "GRN-CI-001", "warehouseCode": "MAIN",
        "lines": [{"productCode": "EYT-PR-001", "quantity": 40}],
    })
    assert first.status_code in (201, 409), first.text

    detail = client.get("/api/purchase/orders/PO-CI-001", headers=auth)
    assert detail.status_code == 200, detail.text
    assert Decimal(str(detail.json()["lines"][0]["remainingQty"])) == Decimal("60")
    assert detail.json()["status"] == "partially_received"

    over = client.post("/api/purchase/orders/PO-CI-001/receive", headers=auth, json={
        "receiptNo": "GRN-CI-OVER", "warehouseCode": "MAIN",
        "lines": [{"productCode": "EYT-PR-001", "quantity": 61}],
    })
    assert over.status_code == 409

    final = client.post("/api/purchase/orders/PO-CI-001/receive", headers=auth, json={
        "receiptNo": "GRN-CI-002", "warehouseCode": "MAIN",
        "lines": [{"productCode": "EYT-PR-001", "quantity": 60}],
    })
    assert final.status_code in (201, 409), final.text

    detail = client.get("/api/purchase/orders/PO-CI-001", headers=auth)
    assert detail.json()["status"] == "received"
    assert Decimal(str(detail.json()["lines"][0]["remainingQty"])) == Decimal("0")

    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        balance = conn.execute("SELECT COALESCE(SUM(CASE WHEN transaction_type IN ('RECEIPT','PRODUCTION_RECEIPT','RETURN','TRANSFER_IN') THEN quantity ELSE -quantity END),0) FROM inventory_transactions WHERE product_code='EYT-PR-001' AND warehouse_code='MAIN'").fetchone()[0]
        audits = conn.execute("SELECT count(*) FROM eyt_audit_logs WHERE action LIKE 'procurement.%' AND correlation_id='ci-purchase-receiving'").fetchone()[0]
    assert Decimal(str(balance)) == Decimal("100.000000")
    assert audits >= 3
