from decimal import Decimal
from uuid import uuid4
import pytest
from fastapi import HTTPException
from api.rubika_workshop_erp_posting import _require_single_product

def test_post_requires_live_single_product():
    with pytest.raises(HTTPException) as exc:
        _require_single_product({"status":"DRAFT_REQUIRES_REVIEW","product_match_status":"NO_MATCH","quantity":3000,"entity_candidates":[]})
    assert exc.value.status_code == 422

def test_post_rejects_ambiguous_match():
    with pytest.raises(HTTPException):
        _require_single_product({"status":"DRAFT_REQUIRES_REVIEW","product_match_status":"LIVE_MASTER_MATCH","quantity":3000,"entity_candidates":[{"product_id":str(uuid4()),"product_code":"A"},{"product_id":str(uuid4()),"product_code":"B"}]})

def test_post_accepts_exact_match():
    p=_require_single_product({"status":"DRAFT_REQUIRES_REVIEW","product_match_status":"LIVE_MASTER_MATCH","quantity":3000,"entity_candidates":[{"product_id":str(uuid4()),"product_code":"X33-BUSH"}]})
    assert p["product_code"]=="X33-BUSH"
