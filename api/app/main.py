from contextlib import contextmanager
import os
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL", "")
APP_ENV = os.getenv("APP_ENV", "development")

app = FastAPI(title="E.Y.T ERP API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Explicit allow-list: no dynamic SQL identifiers from clients.
RESOURCES = {
    "customers": {"table": "customers", "fields": ["name", "phone", "email", "address"]},
    "suppliers": {"table": "suppliers", "fields": ["name", "phone", "email", "address"]},
    "products": {"table": "products", "fields": ["sku", "name", "name_fa", "category_id", "unit"]},
    "warehouses": {"table": "warehouses", "fields": ["code", "name", "name_fa", "address", "is_active"]},
    "purchase-requests": {"table": "purchase_requests", "fields": ["request_no", "requested_by", "warehouse_id", "status", "required_date", "notes"]},
    "purchase-orders": {"table": "purchase_orders", "fields": ["po_no", "supplier_id", "warehouse_id", "request_id", "order_date", "expected_date", "status", "currency", "notes"]},
    "production-orders": {"table": "production_orders", "fields": ["production_no", "product_id", "bom_id", "warehouse_id", "planned_quantity", "completed_quantity", "planned_start", "planned_end", "status", "notes"]},
    "mrp-recommendations": {"table": "mrp_recommendations", "fields": ["mrp_run_id", "product_id", "warehouse_id", "recommendation_type", "required_quantity", "available_quantity", "net_requirement", "recommended_date", "status"]},
    "shortage-alerts": {"table": "material_shortage_alerts", "fields": ["product_id", "warehouse_id", "production_order_id", "mrp_run_id", "required_quantity", "available_quantity", "shortage_quantity", "severity", "status", "notes"]},
    "receivables": {"table": "receivables", "fields": ["receivable_no", "customer_id", "invoice_id", "issue_date", "due_date", "original_amount", "paid_amount", "status", "notes"]},
    "payables": {"table": "payables", "fields": ["payable_no", "supplier_id", "purchase_order_id", "issue_date", "due_date", "original_amount", "paid_amount", "status", "notes"]},
    "cash-transactions": {"table": "cash_transactions", "fields": ["transaction_no", "financial_account_id", "transaction_type", "amount", "transaction_date", "reference_type", "reference_id", "description"]},
}

class RecordIn(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)

@contextmanager
def db():
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            yield conn
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

def resource_or_404(name: str):
    resource = RESOURCES.get(name)
    if not resource:
        raise HTTPException(status_code=404, detail="Unknown ERP resource")
    return resource

def clean_data(resource: dict, data: dict):
    payload = {k: v for k, v in data.items() if k in resource["fields"]}
    if not payload:
        raise HTTPException(status_code=422, detail="No allowed fields supplied")
    return payload

@app.get("/api/v1/health")
def health():
    if not DATABASE_URL:
        return {"status": "ok", "database": "not_configured", "environment": APP_ENV}
    with db() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "database": "ok", "environment": APP_ENV}

@app.get("/api/v1/resources")
def resources():
    return {"resources": [{"name": name, "fields": value["fields"]} for name, value in RESOURCES.items()]}

@app.get("/api/v1/{resource}")
def list_records(resource: str, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    spec = resource_or_404(resource)
    with db() as conn:
        rows = conn.execute(f"SELECT * FROM {spec['table']} ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset)).fetchall()
    return {"items": rows, "limit": limit, "offset": offset}

@app.get("/api/v1/{resource}/{record_id}")
def get_record(resource: str, record_id: str):
    spec = resource_or_404(resource)
    with db() as conn:
        row = conn.execute(f"SELECT * FROM {spec['table']} WHERE id = %s", (record_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    return row

@app.post("/api/v1/{resource}", status_code=201)
def create_record(resource: str, body: RecordIn):
    spec = resource_or_404(resource)
    payload = clean_data(spec, body.data)
    cols = list(payload)
    values = [payload[c] for c in cols]
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO {spec['table']} ({', '.join(cols)}) VALUES ({placeholders}) RETURNING *"
    with db() as conn:
        row = conn.execute(sql, values).fetchone()
        conn.commit()
    return row

@app.patch("/api/v1/{resource}/{record_id}")
def update_record(resource: str, record_id: str, body: RecordIn):
    spec = resource_or_404(resource)
    payload = clean_data(spec, body.data)
    assignments = ", ".join(f"{k} = %s" for k in payload)
    values = list(payload.values()) + [record_id]
    with db() as conn:
        row = conn.execute(f"UPDATE {spec['table']} SET {assignments} WHERE id = %s RETURNING *", values).fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    return row

@app.get("/api/v1/dashboard/summary")
def dashboard_summary():
    checks = {
        "open_receivables": "SELECT COALESCE(SUM(original_amount - paid_amount), 0) AS value FROM receivables WHERE status IN ('OPEN','PARTIAL','OVERDUE')",
        "open_payables": "SELECT COALESCE(SUM(original_amount - paid_amount), 0) AS value FROM payables WHERE status IN ('OPEN','PARTIAL','OVERDUE')",
        "open_shortages": "SELECT COUNT(*) AS value FROM material_shortage_alerts WHERE status IN ('OPEN','ACKNOWLEDGED')",
        "active_production": "SELECT COUNT(*) AS value FROM production_orders WHERE status IN ('PLANNED','RELEASED','IN_PROGRESS','PAUSED')",
        "queued_automation": "SELECT COUNT(*) AS value FROM automation_jobs WHERE status IN ('QUEUED','RUNNING')",
    }
    with db() as conn:
        data = {key: conn.execute(sql).fetchone()["value"] for key, sql in checks.items()}
    return data
