"""Compatibility FastAPI application."""
try:
    from fastapi import FastAPI
except ImportError:  # pragma: no cover
    FastAPI = None

if FastAPI is not None:
    app = FastAPI(title="E.Y.T Production API", version="1.0.0")
    from .inventory_api import router as inventory_router
    from .core_master_api import router as core_master_router
    app.include_router(inventory_router)
    app.include_router(core_master_router)
else:
    app = None
