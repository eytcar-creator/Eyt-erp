from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_order_profitability_uses_zero_cost_fallback_consistently():
    migration = (ROOT / "database/migrations/039_eyt_profitability_integrity.sql").read_text(encoding="utf-8")
    assert "NULLIF(i.actual_cost_snapshot,0)" in migration
    assert "NULLIF(i.cost_snapshot,0)" in migration
    assert "actual_cogs" in migration
    assert "AS cogs" in migration
    assert "AS contribution_profit" in migration


def test_profitability_excludes_draft_and_cancelled_orders():
    migration = (ROOT / "database/migrations/039_eyt_profitability_integrity.sql").read_text(encoding="utf-8")
    assert "WHERE o.status IN ('CONFIRMED','FULFILLED')" in migration
    assert "JOIN sales_orders o ON o.id=i.sales_order_id" in migration


def test_ai_finance_missing_cost_detector_uses_same_order_states():
    source = (ROOT / "api/production/ai_finance_api.py").read_text(encoding="utf-8")
    assert "so.status IN ('CONFIRMED','FULFILLED')" in source
    assert "COALESCE(NULLIF(soi.actual_cost_snapshot,0)," in source
    assert "NULLIF(soi.cost_snapshot,0)) IS NULL" in source
