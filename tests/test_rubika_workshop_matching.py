from api.rubika_workshop_matching import build_draft, candidate_entities


def test_x33_alias_match():
    matches = candidate_entities("بوش X33 تعداد 3000")
    assert matches
    assert matches[0]["canonical_name"] == "X33"
    assert matches[0]["confidence"] == 0.95


def test_draft_never_mutates_erp():
    draft = build_draft(
        {"message_type": "PRODUCTION", "quantity": 3000, "amount_toman": None},
        "بوش X33 تعداد 3000",
    )
    assert draft["status"] == "DRAFT_REQUIRES_REVIEW"
    assert draft["erp_mutation"] is False
    assert "PRODUCT_MATCH" in draft["required_review"]
