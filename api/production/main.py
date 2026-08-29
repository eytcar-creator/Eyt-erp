from fastapi import FastAPI

from .fastapi_app import app as base_app
from .operation_api import router as operation_router
from .auth import router as auth_router
from .costing_api import router as costing_router
from .dashboard_api import router as dashboard_router
from .sales_api import router as sales_router
from .procurement_api import router as procurement_router
from .finance_router import router as finance_router

app = base_app or FastAPI(title="E.Y.T ERP API", version="0.5.0")
app.include_router(auth_router)
app.include_router(operation_router)
app.include_router(costing_router)
app.include_router(dashboard_router)
app.include_router(sales_router)
app.include_router(procurement_router)
app.include_router(finance_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "eyt-erp", "version": "0.5.0"}
