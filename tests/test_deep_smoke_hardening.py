from pathlib import Path

import pytest

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


def test_migration_verifier_recognizes_four_digit_sql_migration_ids():
    from scripts.verify_migration_chain import MIGRATION_RE

    assert MIGRATION_RE.match("999_rubika_workshop_gateway.sql")
    assert MIGRATION_RE.match("1000_rubika_workshop_erp_posting.sql")
    assert not MIGRATION_RE.match("1000rubika_workshop_erp_posting.sql")


def test_migration_verifier_allows_multiple_migrations_on_same_date(tmp_path):
    from scripts.verify_migration_chain import verify

    for number in range(1, 12):
        (tmp_path / f"{number:03d}_legacy_{number}.sql").write_text("-- test\n", encoding="utf-8")
    (tmp_path / "20260908_production_control_hardening.sql").write_text("-- test\n", encoding="utf-8")
    (tmp_path / "20260908_production_inventory_wip.sql").write_text("-- test\n", encoding="utf-8")

    verify(tmp_path)


def test_migration_verifier_rejects_duplicate_sequence_ids(tmp_path):
    from scripts.verify_migration_chain import verify

    for number in range(1, 12):
        (tmp_path / f"{number:03d}_legacy_{number}.sql").write_text("-- test\n", encoding="utf-8")
    (tmp_path / "1000_first.sql").write_text("-- test\n", encoding="utf-8")
    (tmp_path / "1000_second.sql").write_text("-- test\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="duplicate migration numbers"):
        verify(tmp_path)


def test_bootstrap_serializes_concurrent_first_user_creation():
    text = (ROOT / "api/production/auth.py").read_text(encoding="utf-8")
    assert "pg_advisory_xact_lock(hashtextextended('eyt-erp-bootstrap', 0))" in text
