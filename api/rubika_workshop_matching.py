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
    # Known E.Y.T common family. "سیکا ۰۳" is intentionally not accepted.
    "jac j4": "3K000",
    "j4": "3K000",
    "jac s3": "3K000",
    "s3": "3K000",
    "changan": "3K000",
    "سیکا ۳۰": "3K000",
    "سیکا30": "3K000",
    "3k000": "3K000",
}


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"\s+", " ", text)
    return text


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


def _live_product_candidates(cur: Any, text: str) -> list[dict[str, Any]]:
    normalized = normalize_text(text)
    found: dict[int, dict[str, Any]] = {}

    # Search the canonical Product Master, not a second hard-coded product list.
    # The query is intentionally read-only and returns only active products.
    sql = """
        SELECT DISTINCT
            p.id, p.sku, p.product_code, p.name_fa, p.name_en,
            p.oem_code, pa.alias, pa.alias_type
        FROM products p
        LEFT JOIN product_aliases pa ON pa.product_id = p.id
        WHERE p.is_active = TRUE
          AND (
              lower(coalesce(p.sku, '')) = lower(%s)
              OR lower(coalesce(p.product_code, '')) = lower(%s)
              OR lower(coalesce(p.oem_code, '')) = lower(%s)
              OR lower(coalesce(p.name_fa, '')) = lower(%s)
              OR lower(coalesce(p.name_en, '')) = lower(%s)
              OR lower(coalesce(pa.alias, '')) = lower(%s)
          )
        ORDER BY p.product_code
        LIMIT 200
    """

    terms: list[tuple[str, str]] = []
    for alias, canonical in KNOWN_ALIASES.items():
        if normalize_text(alias) in normalized:
            terms.append((alias, canonical))

    # Also allow an explicit SKU/product code appearing in the message.
    tokens = re.findall(r"[A-Za-z0-9آ-ی][A-Za-z0-9آ-ی._-]{1,49}", text)
    for token in tokens:
        terms.append((token, token))

    for term, canonical in terms:
        cur.execute(sql, (term, term, term, term, term, term))
        for row in cur.fetchall():
            product_id, sku, product_code, name_fa, name_en, oem_code, alias, alias_type = row
            if product_id in found:
                continue
            matched_alias = alias if alias and normalize_text(alias) in normalized else term
            method = "PRODUCT_ALIAS" if alias and normalize_text(alias) in normalized else "PRODUCT_MASTER"
            confidence = 0.98 if method == "PRODUCT_ALIAS" else 0.96
            found[product_id] = {
                "entity_type": "PRODUCT",
                "product_id": str(product_id),
                "sku": sku,
                "product_code": product_code,
                "name_fa": name_fa,
                "name_en": name_en,
                "oem_code": oem_code,
                "canonical_name": product_code or name_fa,
                "matched_alias": matched_alias,
                "alias_type": alias_type,
                "match_method": method,
                "confidence": confidence,
            }

    return list(found.values())


def build_draft(
    proposal: dict[str, Any],
    text: str,
    cur: Any | None = None,
) -> dict[str, Any]:
    live_candidates = _live_product_candidates(cur, text) if cur is not None else []
    fallback_candidates = candidate_entities(text) if not live_candidates else []

    candidates = live_candidates or fallback_candidates
    product_match_status = (
        "LIVE_MASTER_MATCH"
        if live_candidates
        else ("KNOWN_ALIAS_REVIEW" if fallback_candidates else "NO_MATCH")
    )

    return {
        "schema_version": "rubika-workshop-draft-v2",
        "source": "RUBIKA_WORKSHOP",
        "message_type": proposal.get("message_type"),
        "entity_candidates": candidates,
        "product_match_status": product_match_status,
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
