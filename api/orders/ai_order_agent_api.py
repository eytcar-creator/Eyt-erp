from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from .ai_order_agent import AIOrderAgent

router = APIRouter(prefix="/api/v1/ai-order-agent", tags=["E.Y.T One - AI Order Agent"])
agent = AIOrderAgent()


class ProposalIn(BaseModel):
    text: str
    customer_id: str | None = None


@router.post("/propose")
def propose_order(payload: ProposalIn) -> dict[str, Any]:
    """Return a structured order proposal only. No ERP mutation occurs here."""
    return agent.propose(payload.text, payload.customer_id)
