from contextlib import contextmanager
import os
from typing import Any

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "")
APP_ENV = os.getenv("APP_ENV", "development")
engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)) if DATABASE_URL else None

app = FastAPI(title="E.Y.T ERP API", version="1.2.0")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",")], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

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

def resource_or_404(name):
    resource = RESOURCES.get(name)
    if not resource:
        raise HTTPException(status_code=404, detail="Unknown ERP resource")
    return resource

def clean_data(resource, data):
    values = {k: v for k, v in data.items() if k in resource["fields"]}
    if not values:
        raise HTTPException(status_code=422, detail="No allowed fields supplied")
    return values

from app.auth.service import current_principal

@app.get("/api/v1/health")
async def health():
    if engine is None:
        return {"status": "ok", "database": "not_configured", "environment": APP_ENV}
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok", "environment": APP_ENV}

@app.get("/api/v1/resources")
async def resources(principal: dict = Depends(current_principal)):
    return {"resources": [{"name": n, "fields": v["fields"]} for n, v in RESOURCES.items()]}

@app.get("/api/v1/{resource}")
async def list_records(resource: str, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), principal: dict = Depends(current_principal)):
    s = resource_or_404(resource)
    async with engine.connect() as conn:
        result = await conn.execute(text(f"SELECT * FROM {s['table']} ORDER BY id DESC LIMIT :limit OFFSET :offset"), {"limit": limit, "offset": offset})
        return {"items": [dict(row._mapping) for row in result], "limit": limit, "offset": offset}

@app.get("/api/v1/{resource}/{record_id}")
async def get_record(resource: str, record_id: str, principal: dict = Depends(current_principal)):
    s = resource_or_404(resource)
    async with engine.connect() as conn:
        row = (await conn.execute(text(f"SELECT * FROM {s['table']} WHERE id = :id"), {"id": record_id})).first()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    return dict(row._mapping)

@app.post("/api/v1/{resource}", status_code=201)
async def create_record(resource: str, body: RecordIn, principal: dict = Depends(current_principal)):
    s = resource_or_404(resource)
    values = clean_data(s, body.data)
    columns = list(values)
    async with engine.begin() as conn:
        result = await conn.execute(text(f"INSERT INTO {s['table']} ({', '.join(columns)}) VALUES ({', '.join(':' + k for k in columns)}) RETURNING *"), values)
        return dict(result.first()._mapping)

@app.patch("/api/v1/{resource}/{record_id}")
async def update_record(resource: str, record_id: str, body: RecordIn, principal: dict = Depends(current_principal)):
    s = resource_or_404(resource)
    values = clean_data(s, body.data)
    async with engine.begin() as conn:
        result = await conn.execute(text(f"UPDATE {s['table']} SET " + ", ".join(f"{k} = :{k}" for k in values) + " WHERE id = :record_id RETURNING *"), {**values, "record_id": record_id})
        row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    return dict(row._mapping)

@app.get("/api/v1/dashboard/finance-summary")
async def finance_dashboard(principal: dict = Depends(current_principal)):
    checks = {
        "open_receivables": "SELECT COALESCE(SUM(original_amount-paid_amount),0) value FROM receivables WHERE status IN ('OPEN','PARTIAL','OVERDUE')",
        "open_payables": "SELECT COALESCE(SUM(original_amount-paid_amount),0) value FROM payables WHERE status IN ('OPEN','PARTIAL','OVERDUE')",
        "open_shortages": "SELECT COUNT(*) value FROM material_shortage_alerts WHERE status IN ('OPEN','ACKNOWLEDGED')",
        "active_production": "SELECT COUNT(*) value FROM production_orders WHERE status IN ('PLANNED','RELEASED','IN_PROGRESS','PAUSED')",
        "queued_automation": "SELECT COUNT(*) value FROM automation_jobs WHERE status IN ('QUEUED','RUNNING')",
    }
    async with engine.connect() as conn:
        return {k: (await conn.execute(text(v))).scalar_one() for k, v in checks.items()}

from app.auth.api import router as auth_router
from app.erp import router as erp_router
app.include_router(auth_router)
app.include_router(erp_router)
