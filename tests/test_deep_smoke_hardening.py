from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_upgrade_runner_includes_current_post_init_migrations():
    text = (ROOT / "scripts/migrate_production.py").read_text(encoding="utf-8")
    for name in (
        "20260908_production_control_hardening.sql",
        "20260908_production_inventory_wip.sql",
        "20260908_production_payments.sql",
        "035_deep_smoke_hardening.sql",
    ):
        assert name in text


def test_production_compose_requires_auth_secrets():
    text = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    assert "JWT_SECRET: ${JWT_SECRET:?JWT_SECRET must be set}" in text
    assert "BOOTSTRAP_SECRET: ${BOOTSTRAP_SECRET:?BOOTSTRAP_SECRET must be set}" in text


def test_legacy_material_issue_and_return_populate_actual_cost_fields():
    text = (ROOT / "api/production/inventory_production_api.py").read_text(encoding="utf-8")
    assert "component_product_id,unit_cost,quantity_source" in text
    assert "WIP_TRANSFER_OUT','WIP_ISSUE','WIP_CONSUMPTION" in text


def test_profitability_excludes_non_revenue_order_states():
    text = (ROOT / "database/migrations/035_deep_smoke_hardening.sql").read_text(encoding="utf-8")
    assert "DRAFT','PENDING_CONFIRMATION','CANCELLED','RETURNED" in text
