from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from .ai_order_agent import AIOrderAgent
from .resolution_service import ResolutionService

router = APIRouter(prefix="/api/v1/ai-order-agent", tags=["E.Y.T One - AI Order Agent"])
agent = AIOrderAgent()
resolver = ResolutionService()


class ProposalIn(BaseModel):
    text: str
    customer_id: str | None = None


class ResolveIn(BaseModel):
    customer_id: str | None = None
    customer_code: str | None = None
    customer_phone: str | None = None
    customer_name: str | None = None
    product_identifier: str | None = None
    product_name: str | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None


@router.post("/propose")
def propose_order(payload: ProposalIn) -> dict[str, Any]:
    """Return a structured order proposal only. No ERP mutation occurs here."""
    return agent.propose(payload.text, payload.customer_id)


@router.post("/resolve")
def resolve_order_entities(payload: ResolveIn) -> dict[str, Any]:
    """Resolve existing Customer/Product Master records without mutating ERP state."""
    customer = resolver.resolve_customer(
        customer_id=payload.customer_id,
        customer_code=payload.customer_code,
        phone=payload.customer_phone,
        name=payload.customer_name,
    )
    product = resolver.resolve_product(
        identifier=payload.product_identifier,
        name=payload.product_name,
        vehicle_make=payload.vehicle_make,
        vehicle_model=payload.vehicle_model,
    )
    ready = customer["status"] == "EXACT" and product["status"] == "EXACT"
    return {
        "customer": customer,
        "product": product,
        "ready_for_commercial_gate": ready,
        "next_action": "PRICE_STOCK_CREDIT_GATE" if ready else "RESOLVE_AMBIGUITY",
    }
