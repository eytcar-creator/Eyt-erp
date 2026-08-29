from fastapi import FastAPI

from .fastapi_app import app as base_app
from .operation_api import router as operation_router
from .auth import router as auth_router
from .costing_api import router as costing_router
from .dashboard_api import router as dashboard_router

app = base_app or FastAPI(title="E.Y.T Production API", version="0.4.0")
app.include_router(auth_router)
app.include_router(operation_router)
app.include_router(costing_router)
app.include_router(dashboard_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "eyt-production", "version": "0.4.0"}
