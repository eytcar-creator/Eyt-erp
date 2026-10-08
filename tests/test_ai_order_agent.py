from api.orders.ai_order_agent import AIOrderAgent

def test_proposal_requires_confirmation():
    result = AIOrderAgent().propose("code 3K000 quantity 20", customer_id="customer-1")
    assert result["items"][0]["product_code"] == "3K000"
    assert result["items"][0]["quantity"] == "20"
    assert result["needs_confirmation"] is True

def test_unknown_message_does_not_create_order():
    result = AIOrderAgent().propose("I need some suspension parts")
    assert result["items"] == []
    assert result["needs_confirmation"] is True
