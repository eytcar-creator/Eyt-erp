from decimal import Decimal
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .auth import audit, require_permission
from .postgres_repository import PostgresProductionRepository

router = APIRouter(prefix="/api/production/orders", tags=["production"])


class OperationStartInput(BaseModel):
    sequenceNo: int
    operationCode: str
    operationName: str
    contractorName: str | None = None


class OperationCompletionInput(BaseModel):
    sequenceNo: int
    operationCode: str
    operationName: str
    inputQty: Decimal
    acceptedQty: Decimal
    rejectedQty: Decimal = Decimal("0")
    wasteQty: Decimal = Decimal("0")
    serviceCost: Decimal = Decimal("0")
    transportCost: Decimal = Decimal("0")
    contractorName: str | None = None


def validate_quantities(payload: OperationCompletionInput) -> None:
    values = (payload.inputQty, payload.acceptedQty, payload.rejectedQty, payload.wasteQty)
    if min(values) < 0:
        raise HTTPException(status_code=422, detail="Production quantities cannot be negative")
    if payload.acceptedQty + payload.rejectedQty + payload.wasteQty != payload.inputQty:
        raise HTTPException(status_code=409, detail="accepted + rejected + waste must equal input")


def _repo() -> PostgresProductionRepository:
    import psycopg
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    return PostgresProductionRepository(psycopg.connect(database_url))


def _order_id(repo: PostgresProductionRepository, order_no: str):
    order = repo.get_order(order_no)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Production order not found: {order_no}")
    return order["id"]


@router.post("/{order_no}/operations/{operation_code}/start", status_code=200)
def start_operation(
    order_no: str,
    operation_code: str,
    payload: OperationStartInput,
    request: Request,
    principal: dict = Depends(require_permission("production.execute")),
):
    if payload.operationCode != operation_code:
        raise HTTPException(status_code=409, detail="operationCode does not match URL")
    repo = _repo()
    try:
        entity_id = _order_id(repo, order_no)
        repo.start_operation(order_no, payload.sequenceNo, operation_code,
                             payload.operationName, payload.contractorName)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        repo.connection.close()
    audit(request, principal, "production.operation.start", entity_id,
          {"operation_code": operation_code, "sequence_no": payload.sequenceNo})
    return {"orderNo": order_no, "operationCode": operation_code, "status": "in_progress"}


@router.post("/{order_no}/operations/{operation_code}/complete", status_code=200)
def complete_operation_http(
    order_no: str,
    operation_code: str,
    payload: OperationCompletionInput,
    request: Request,
    principal: dict = Depends(require_permission("production.execute")),
):
    if payload.operationCode != operation_code:
        raise HTTPException(status_code=409, detail="operationCode does not match URL")
    validate_quantities(payload)
    repo = _repo()
    try:
        entity_id = _order_id(repo, order_no)
        repo.record_operation(
            order_no, payload.sequenceNo, operation_code, payload.operationName,
            payload.inputQty, payload.acceptedQty, payload.rejectedQty,
            payload.wasteQty, payload.serviceCost, payload.transportCost,
            payload.contractorName,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        repo.connection.close()
    audit(request, principal, "production.operation.complete", entity_id,
          {"operation_code": operation_code, "sequence_no": payload.sequenceNo,
           "accepted_qty": str(payload.acceptedQty), "rejected_qty": str(payload.rejectedQty),
           "waste_qty": str(payload.wasteQty)})
    return {"orderNo": order_no, "operationCode": operation_code, "status": "completed"}
