from decimal import Decimal
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from .auth import audit, require_permission
from .postgres_repository import PostgresProductionRepository
router=APIRouter(prefix="/api/production/orders",tags=["production"])
class OperationStartInput(BaseModel):
    sequenceNo:int; operationCode:str; operationName:str; contractorName:str|None=None
class OperationCompletionInput(BaseModel):
    sequenceNo:int; operationCode:str; operationName:str; inputQty:Decimal; acceptedQty:Decimal; rejectedQty:Decimal=Decimal("0"); wasteQty:Decimal=Decimal("0"); serviceCost:Decimal=Decimal("0"); transportCost:Decimal=Decimal("0"); contractorName:str|None=None

def validate_quantities(p):
    values=(p.inputQty,p.acceptedQty,p.rejectedQty,p.wasteQty)
    if min(values)<0: raise HTTPException(422,"Production quantities cannot be negative")
    if p.acceptedQty+p.rejectedQty+p.wasteQty!=p.inputQty: raise HTTPException(409,"accepted + rejected + waste must equal input")
    if p.serviceCost<0 or p.transportCost<0: raise HTTPException(422,"Costs cannot be negative")
def _repo():
    import psycopg
    url=os.getenv("DATABASE_URL")
    if not url: raise HTTPException(500,"DATABASE_URL is not configured")
    return PostgresProductionRepository(psycopg.connect(url))
def _order_id(repo,order_no):
    order=repo.get_order(order_no)
    if order is None: raise HTTPException(404,f"Production order not found: {order_no}")
    return order["id"]
@router.post("/{order_no}/operations/{operation_code}/start")
def start_operation(order_no,operation_code,payload:OperationStartInput,request:Request,principal:dict=Depends(require_permission("production.execute"))):
    if payload.operationCode!=operation_code: raise HTTPException(409,"operationCode does not match URL")
    repo=_repo()
    try:
        entity_id=_order_id(repo,order_no)
        repo.start_operation(order_no,payload.sequenceNo,operation_code,payload.operationName,payload.contractorName)
    except (KeyError,ValueError) as exc: raise HTTPException(409,str(exc)) from exc
    finally: repo.connection.close()
    audit(request,principal,"production.operation.start",entity_id,{"operation_code":operation_code,"sequence_no":payload.sequenceNo})
    return {"orderNo":order_no,"operationCode":operation_code,"status":"in_progress"}
@router.post("/{order_no}/operations/{operation_code}/complete")
def complete_operation_http(order_no,operation_code,payload:OperationCompletionInput,request:Request,principal:dict=Depends(require_permission("production.execute"))):
    if payload.operationCode!=operation_code: raise HTTPException(409,"operationCode does not match URL")
    validate_quantities(payload); repo=_repo()
    try:
        entity_id=_order_id(repo,order_no)
        repo.record_operation(order_no,payload.sequenceNo,operation_code,payload.operationName,payload.inputQty,payload.acceptedQty,payload.rejectedQty,payload.wasteQty,payload.serviceCost,payload.transportCost,payload.contractorName)
        with repo.connection.cursor() as cur:
            cur.execute("SELECT product_code FROM production_orders WHERE id=%s",(entity_id,)); product=cur.fetchone()[0]
            cur.execute("INSERT INTO production_inventory_ledger(production_order_id,warehouse_code,movement_type,quantity,unit,reference_no,actor_name,notes) VALUES(%s,'MAIN','WIP_RECEIPT',%s,'pcs',%s,%s,%s)",(entity_id,payload.acceptedQty,order_no,principal["username"],operation_code))
            if payload.wasteQty>0:
                cur.execute("INSERT INTO production_scrap(production_order_id,product_code,quantity,unit,reason,actor_name,notes) VALUES(%s,%s,%s,'pcs','operation waste',%s,%s)",(entity_id,product,payload.wasteQty,principal["username"],operation_code))
            total=payload.serviceCost+payload.transportCost
            if total>0 and payload.contractorName:
                cur.execute("INSERT INTO production_service_payables(production_order_id,contractor_name,service_amount,transport_amount,status,notes) VALUES(%s,%s,%s,%s,'open',%s)",(entity_id,payload.contractorName,payload.serviceCost,payload.transportCost,operation_code))
            repo.connection.commit()
    except (KeyError,ValueError) as exc: raise HTTPException(409,str(exc)) from exc
    finally: repo.connection.close()
    audit(request,principal,"production.operation.complete",entity_id,{"operation_code":operation_code,"sequence_no":payload.sequenceNo,"accepted_qty":str(payload.acceptedQty),"rejected_qty":str(payload.rejectedQty),"waste_qty":str(payload.wasteQty)})
    return {"orderNo":order_no,"operationCode":operation_code,"status":"completed"}
