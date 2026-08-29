from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .auth import require_permission

router = APIRouter(prefix="/api/inventory", tags=["inventory-flow"])

class StockLine(BaseModel):
    sku: str
    quantity: Decimal = Field(gt=0)

class StockFlow(BaseModel):
    documentNo: str
    warehouse: str
    lines: list[StockLine] = Field(min_length=1)

class StockBalance(BaseModel):
    sku: str
    available: Decimal = Field(ge=0)
    reserved: Decimal = Field(default=Decimal("0"), ge=0)

@router.post("/reserve")
def reserve(payload: StockFlow, _=Depends(require_permission("inventory.write"))):
    return {"documentNo": payload.documentNo, "warehouse": payload.warehouse, "status": "reserved", "lines": [x.model_dump() for x in payload.lines]}

@router.post("/issue")
def issue(payload: StockFlow, _=Depends(require_permission("inventory.write"))):
    return {"documentNo": payload.documentNo, "warehouse": payload.warehouse, "status": "issued", "lines": [x.model_dump() for x in payload.lines]}

@router.post("/receive")
def receive(payload: StockFlow, _=Depends(require_permission("inventory.write"))):
    return {"documentNo": payload.documentNo, "warehouse": payload.warehouse, "status": "received", "lines": [x.model_dump() for x in payload.lines]}

@router.post("/balance/check")
def check_balance(payload: StockBalance, _=Depends(require_permission("inventory.read"))):
    if payload.reserved > payload.available:
        raise HTTPException(409, "reserved quantity exceeds available stock")
    return {"sku": payload.sku, "available": payload.available, "reserved": payload.reserved, "free": payload.available-payload.reserved}
