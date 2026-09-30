from api.production.finance_reconciliation_rules import evaluate_reconciliation


def test_reconciliation_ok():
    result = evaluate_reconciliation(1000, 800, 500, 300, 200)
    assert result.status == "OK"
    assert result.issues == ()


def test_customer_collected_exceeds_receivable():
    result = evaluate_reconciliation(1000, 1100, 500, 300, 200)
    assert result.status == "ALERT"
    assert "customer_collected_exceeds_receivable" in result.issues


def test_production_paid_exceeds_payable():
    result = evaluate_reconciliation(1000, 800, 500, 600, 200)
    assert result.status == "ALERT"
    assert "production_paid_exceeds_payable" in result.issues


def test_negative_funding_balance():
    result = evaluate_reconciliation(1000, 800, 500, 300, -1)
    assert result.status == "ALERT"
    assert "active_funding_balance_negative" in result.issues


def test_multiple_reconciliation_issues():
    result = evaluate_reconciliation(1000, 1100, 500, 600, -1)
    assert result.status == "ALERT"
    assert set(result.issues) == {
        "customer_collected_exceeds_receivable",
        "production_paid_exceeds_payable",
        "active_funding_balance_negative",
    }
