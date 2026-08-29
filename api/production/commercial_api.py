from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .auth import require_permission

router = APIRouter(prefix="/api/commercial", tags=["commercial"])

class Party(BaseModel):
    code: str
    name: str
    phone: str | None = None
    taxId: str | None = None
    address: str | None = None
    creditLimit: Decimal = Field(default=Decimal("0"), ge=0)

class OrderLine(BaseModel):
    sku: str
    name: str
    qty: Decimal = Field(gt=0)
    unitPrice: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)

class SalesOrder(BaseModel):
    orderNo: str
    customerCode: str
    lines: list[OrderLine]
    prepayment: Decimal = Field(default=Decimal("0"), ge=0)

class PurchaseOrder(BaseModel):
    orderNo: str
    supplierCode: str
    lines: list[OrderLine]
    prepayment: Decimal = Field(default=Decimal("0"), ge=0)

def total(lines: list[OrderLine]) -> Decimal:
    return sum((x.qty * x.unitPrice - x.discount for x in lines), Decimal("0"))

@router.post("/customers")
def create_customer(payload: Party, _=Depends(require_permission("sales.write"))):
    return {"type":"customer", **payload.model_dump()}

@router.post("/suppliers")
def create_supplier(payload: Party, _=Depends(require_permission("procurement.write"))):
    return {"type":"supplier", **payload.model_dump()}

@router.post("/sales-orders")
def create_sales_order(payload: SalesOrder, _=Depends(require_permission("sales.write"))):
    gross = total(payload.lines)
    if payload.prepayment > gross:
        raise HTTPException(422, "prepayment cannot exceed order total")
    return {"orderNo": payload.orderNo, "customerCode": payload.customerCode, "total": gross, "prepayment": payload.prepayment, "receivable": gross-payload.prepayment, "status":"confirmed"}

@router.post("/purchase-orders")
def create_purchase_order(payload: PurchaseOrder, _=Depends(require_permission("procurement.write"))):
    gross = total(payload.lines)
    if payload.prepayment > gross:
        raise HTTPException(422, "prepayment cannot exceed order total")
    return {"orderNo": payload.orderNo, "supplierCode": payload.supplierCode, "total": gross, "prepayment": payload.prepayment, "payable": gross-payload.prepayment, "status":"confirmed"}
