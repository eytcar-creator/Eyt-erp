from api.rubika_workshop_extraction import extract_message


def test_production_extraction_normalizes_persian_digits():
    result = extract_message("بوش X33 تعداد ۳۰۰۰ عدد تولید شد", "PRODUCTION")
    assert result["message_type"] == "PRODUCTION"
    assert result["quantity"] == 3000
    assert result["erp_mutation"] is False
    assert result["action"] == "REVIEW_REQUIRED"


def test_payment_extraction_separates_amount():
    result = extract_message("برای قالب ۵۰۰۰۰۰ تومان پرداخت شد", "PAYMENT")
    assert result["message_type"] == "PAYMENT"
    assert result["amount_toman"] == 500000
    assert result["quantity"] is None
    assert result["erp_mutation"] is False
