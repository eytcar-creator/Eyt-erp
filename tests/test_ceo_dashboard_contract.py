from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ceo_dashboard_contract():
    source = (ROOT / "api/production/core_master_api.py").read_text(encoding="utf-8")
    assert '@router.get("/ceo/dashboard")' in source
    assert 'require_permission("finance.read")' in source
    assert 'FROM ceo_dashboard' in source
    assert 'FROM sales_orders' in source
    assert 'FROM production_orders' in source
    assert 'FROM quality_inspections' in source
    assert 'FROM production_alerts' in source


def test_ceo_portal_exists_and_is_routed():
    assert (ROOT / "portal/ceo.html").exists()
    source = (ROOT / "api/production/main.py").read_text(encoding="utf-8")
    assert 'def ceo_portal()' in source
    assert 'CEO_PORTAL' in source


def test_finance_read_permission_is_seeded_for_ceo():
    migration = (ROOT / "database/migrations/037_ceo_dashboard_finance_permission.sql").read_text(encoding="utf-8")
    assert "finance.read" in migration
    assert "r.name='CEO'" in migration


def test_actual_cost_order_item_is_uuid():
    source = (ROOT / "api/production/core_master_api.py").read_text(encoding="utf-8")
    assert "from uuid import UUID" in source
    assert "order_item_id: UUID" in source
