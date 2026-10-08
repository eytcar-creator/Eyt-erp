from __future__ import annotations

import re
from typing import Any

KNOWN_ALIASES = {
    "x33": "X33",
    "ایکس۳۳": "X33",
    "ایکس ۳۳": "X33",
    "315": "MVM 315",
    "ام وی ام ۳۱۵": "MVM 315",
    "آریو": "Ario",
    "آریزو": "Arizo",
    "haima s7": "Haima S7",
    "هایما اس۷": "Haima S7",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def candidate_entities(text: str) -> list[dict[str, Any]]:
    normalized = normalize_text(text)
    candidates: list[dict[str, Any]] = []
    for alias, canonical in KNOWN_ALIASES.items():
        if normalize_text(alias) in normalized:
            candidates.append({
                "entity_type": "PRODUCT_FAMILY",
                "canonical_name": canonical,
                "matched_alias": alias,
                "match_method": "KNOWN_ALIAS",
                "confidence": 0.95,
            })
    return candidates


def build_draft(proposal: dict[str, Any], text: str) -> dict[str, Any]:
    candidates = candidate_entities(text)
    return {
        "schema_version": "rubika-workshop-draft-v1",
        "source": "RUBIKA_WORKSHOP",
        "message_type": proposal.get("message_type"),
        "entity_candidates": candidates,
        "quantity": proposal.get("quantity"),
        "amount_toman": proposal.get("amount_toman"),
        "status": "DRAFT_REQUIRES_REVIEW",
        "erp_mutation": False,
        "required_review": [
            "PRODUCT_MATCH",
            "QUANTITY",
            "OPERATION_CONTEXT",
        ],
    }
