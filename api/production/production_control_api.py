"""Production control UI/API contract: orders, operations and traceability."""
from decimal import Decimal
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .auth import audit, require_permission
from .postgres_repository import PostgresProductionRepository

router = APIRouter(prefix="/api/production", tags=["production-control"])

def _repo():
    import psycopg
    url=os.getenv("DATABASE_URL")
    if not url: raise HTTPException(503,"DATABASE_URL is not configured")
    return PostgresProductionRepository(psycopg.connect(url))

class OrderInput(BaseModel):
    order_no: str=Field(min_length=3,max_length=50)
    product_code: str=Field(min_length=1,max_length=100)
    product_name: str=Field(min_length=1,max_length=255)
    target_qty: Decimal=Field(gt=0)
    order_date: str
    customer_id: int|None=None

@router.post("/orders",status_code=201)
def create_order(payload:OrderInput,request:Request,principal:dict=Depends(require_permission("production.execute"))):
    repo=_repo()
    try:
        if repo.get_order(payload.order_no): raise HTTPException(409,"Production order already exists")
        repo.create_order(payload.order_no,payload.product_code,payload.product_name,payload.target_qty,payload.order_date,payload.customer_id)
    finally: repo.connection.close()
    audit(request,principal,"production.order.create",payload.order_no,{"product_code":payload.product_code,"target_qty":str(payload.target_qty)})
    return {"orderNo":payload.order_no,"status":"planned"}

@router.get("/orders/{order_no}")
def get_order(order_no:str,principal:dict=Depends(require_permission("production.read"))):
    repo=_repo()
    try:
        order=repo.get_order(order_no)
        if not order: raise HTTPException(404,"Production order not found")
        with repo.connection.cursor() as cur:
            cur.execute("SELECT sequence_no,operation_code,operation_name,contractor_name,planned_start,planned_end,actual_start,actual_end,input_qty,accepted_qty,rejected_qty,waste_qty,waste_reason,service_cost,transport_cost,status,notes FROM production_operations WHERE production_order_id=%s ORDER BY sequence_no,id",(order["id"],))
            operations=cur.fetchall()
        return {"order":order,"operations":[dict(zip([d.name for d in cur.description],row)) for row in operations]}
    finally: repo.connection.close()
