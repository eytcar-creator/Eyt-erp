import os

from fastapi import FastAPI, HTTPException

from .fastapi_app import app as base_app
from .operation_api import router as operation_router
from .auth import router as auth_router
from .costing_api import router as costing_router
from .dashboard_api import router as dashboard_router
from .sales_api import router as sales_router
from .procurement_api import router as procurement_router
from .finance_router import router as finance_router
from .commercial_api import router as commercial_router
from .inventory_flow_api import router as inventory_flow_router
from .product_master_api import router as product_master_router

app = base_app or FastAPI(title="E.Y.T ERP API", version="0.8.0")
app.include_router(auth_router)
app.include_router(operation_router)
app.include_router(costing_router)
app.include_router(dashboard_router)
app.include_router(sales_router)
app.include_router(procurement_router)
app.include_router(finance_router)
app.include_router(commercial_router)
app.include_router(inventory_flow_router)
app.include_router(product_master_router)

@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "eyt-erp", "version": "0.8.0"}

@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]:
    """Deployment readiness probe: verifies the configured PostgreSQL connection."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    try:
        import psycopg
        with psycopg.connect(database_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database is not ready") from exc
    return {"status": "ready", "service": "eyt-erp", "version": "0.8.0"}
