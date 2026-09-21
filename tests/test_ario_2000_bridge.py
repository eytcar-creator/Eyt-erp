from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_actual_cost_bridge_is_uuid_based():
    sql = (ROOT / "database/migrations/036_eyt_actual_cost_order_bridge.sql").read_text(encoding="utf-8")
    assert "p_order_item_id uuid" in sql
    assert "actual_cost_snapshot = v_cost" in sql
    assert "production_order_id = p_production_order_id" in sql


def test_core_master_api_uses_uuid_order_item_id():
    source = (ROOT / "api/production/core_master_api.py").read_text(encoding="utf-8")
    assert "from uuid import UUID" in source
    assert "order_item_id: UUID" in source
