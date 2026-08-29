"""FastAPI adapter for the E.Y.T production API."""
from decimal import Decimal
import os

try:
    from fastapi import Depends, FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError:  # pragma: no cover
    FastAPI = None

from .postgres_repository import PostgresProductionRepository
from .auth import require_permission

if FastAPI is not None:
    app = FastAPI(title="E.Y.T Production API", version="0.3.0")

    class OrderInput(BaseModel):
        orderNo: str
        productCode: str
        productName: str
        targetQty: Decimal
        orderDate: str
        customerId: int | None = None

    @app.get("/api/production/orders/{order_no}")
    def get_order(order_no: str, _=Depends(require_permission("production.read"))):
        import psycopg
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
        with psycopg.connect(database_url) as conn:
            result = PostgresProductionRepository(conn).get_order(order_no)
        if result is None:
            raise HTTPException(status_code=404, detail="Production order not found")
        return result

    @app.post("/api/production/orders", status_code=201)
    def create_order(payload: OrderInput, _=Depends(require_permission("production.execute"))):
        import psycopg
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
        with psycopg.connect(database_url) as conn:
            PostgresProductionRepository(conn).create_order(payload.orderNo, payload.productCode, payload.productName, payload.targetQty, payload.orderDate, payload.customerId)
        return {"orderNo": payload.orderNo, "status": "planned"}

    # Sprint 4 routers are imported here so the Docker entrypoint remains stable.
    from .inventory_api import router as inventory_router
    app.include_router(inventory_router)
else:
    app = None
