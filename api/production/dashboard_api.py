from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .auth import require_permission
from .dashboard import OperationSnapshot, summarize_operations

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class OperationInput(BaseModel):
    code: str
    name: str
    status: str
    acceptedQty: Decimal = Decimal("0")
    rejectedQty: Decimal = Decimal("0")
    wasteQty: Decimal = Decimal("0")


class DashboardInput(BaseModel):
    operations: list[OperationInput] = []


@router.post("/production-summary")
def production_summary(payload: DashboardInput, _=Depends(require_permission("production.read"))):
    snapshots = [
        OperationSnapshot(
            code=o.code,
            name=o.name,
            status=o.status,
            accepted_qty=o.acceptedQty,
            rejected_qty=o.rejectedQty,
            waste_qty=o.wasteQty,
        )
        for o in payload.operations
    ]
    return summarize_operations(snapshots)
