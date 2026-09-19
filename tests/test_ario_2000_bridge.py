from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_actual_cost_bridge_function_is_canonical_uuid_based():
    text = (ROOT / "database/migrations/036_eyt_actual_cost_order_bridge.sql").read_text(encoding="utf-8")
    assert "p_order_item_id uuid" in text
    assert "eyt_apply_actual_production_cost_to_order_line" in text
    assert "actual_cost_snapshot = v_cost" in text
    assert "contribution = quantity * (unit_price - v_cost)" in text


def test_core_master_api_uses_uuid_order_item_id():
    text = (ROOT / "api/production/core_master_api.py").read_text(encoding="utf-8")
    assert "order_item_id: UUID" in text
