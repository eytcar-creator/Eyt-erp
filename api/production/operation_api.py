from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .postgres_repository import PostgresProductionRepository

router = APIRouter(prefix="/api/production/orders", tags=["production"])


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
    if min(payload.inputQty, payload.acceptedQty, payload.rejectedQty, payload.wasteQty) < 0:
        raise HTTPException(status_code=422, detail="Production quantities cannot be negative")
    if payload.acceptedQty + payload.rejectedQty + payload.wasteQty != payload.inputQty:
        raise HTTPException(status_code=409, detail="accepted + rejected + waste must equal input")


# Factory is injected by the application in deployment; kept separate from
# route definitions so tests can use a fake repository.
def complete_operation(repo: PostgresProductionRepository, order_no: str, payload: OperationCompletionInput):
    validate_quantities(payload)
    repo.record_operation(
        order_no,
        payload.sequenceNo,
        payload.operationCode,
        payload.operationName,
        payload.inputQty,
        payload.acceptedQty,
        payload.rejectedQty,
        payload.wasteQty,
        payload.serviceCost,
        payload.transportCost,
        payload.contractorName,
    )
    return {"orderNo": order_no, "operationCode": payload.operationCode, "status": "completed"}
