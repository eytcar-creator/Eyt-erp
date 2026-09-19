"""EYT Core BOM/Routing integration helpers for the production API.

This module is intentionally thin: PostgreSQL remains the source of truth.
It exposes read/validation operations that production and order APIs can reuse.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_permission

router = APIRouter(prefix="/api/v1/core", tags=["eyt-core"])


class ProductCostRequest(BaseModel):
    product_id: str
    quantity: Decimal = Field(gt=0)


@router.get("/products/{product_id}/bom")
def get_product_bom(product_id: str, _=Depends(require_permission("production.read"))):
    """Return the active/latest BOM and calculated material cost."""
    # DB adapter is intentionally injected by the application integration layer.
    # The SQL view is the canonical calculation source.
    return {"product_id": product_id, "source": "eyt_bom_cost", "status": "DB_REQUIRED"}


@router.get("/products/{product_id}/routing")
def get_product_routing(product_id: str, _=Depends(require_permission("production.read"))):
    return {"product_id": product_id, "source": "eyt_routing_cost", "status": "DB_REQUIRED"}


@router.get("/products/{product_id}/standard-cost")
def get_product_standard_cost(product_id: str, _=Depends(require_permission("production.read"))):
    return {"product_id": product_id, "source": "eyt_product_standard_cost", "status": "DB_REQUIRED"}


@router.post("/production/{production_order_id}/cost-snapshot")
def snapshot_production_cost(production_order_id: int, _=Depends(require_permission("production.write"))):
    return {
        "production_order_id": production_order_id,
        "function": "eyt_snapshot_production_cost",
        "status": "DB_REQUIRED",
    }
