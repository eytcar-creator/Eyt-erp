"""Compatibility FastAPI application."""
try:
    from fastapi import FastAPI
except ImportError:  # pragma: no cover
    FastAPI = None

if FastAPI is not None:
    app = FastAPI(title="E.Y.T Production API", version="1.0.0")
    from .inventory_api import router as inventory_router
    from .core_master_api import router as core_master_router
    from .production_control_api import router as production_control_router
    from .inventory_production_api import router as inventory_production_router
    app.include_router(inventory_router)
    app.include_router(core_master_router)
    app.include_router(production_control_router)
    app.include_router(inventory_production_router)
else:
    app = None
