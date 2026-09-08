"""Compatibility FastAPI application. Production order endpoints live in production_control_api."""
import os
try:
    from fastapi import FastAPI
except ImportError:  # pragma: no cover
    FastAPI = None

if FastAPI is not None:
    app = FastAPI(title="E.Y.T Production API", version="0.9.2")
    from .inventory_api import router as inventory_router
    app.include_router(inventory_router)
else:
    app = None
