from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_automation_outbox_registered():
    migration = ROOT / "database" / "migrations" / "039_automation_event_outbox.sql"
    runner = ROOT / "scripts" / "migrate_production.py"
    assert migration.exists()
    assert "039_automation_event_outbox.sql" in runner.read_text(encoding="utf-8")


def test_automation_api_is_mounted():
    main = (ROOT / "api" / "production" / "main.py").read_text(encoding="utf-8")
    api = ROOT / "api" / "production" / "automation_api.py"
    assert api.exists()
    assert "automation_router" in main
    text = api.read_text(encoding="utf-8")
    assert "/api/v1/automation" in text
    assert "automation.read" in text
    assert "automation.write" in text


def test_automation_outbox_has_core_triggers():
    sql = (ROOT / "database" / "migrations" / "039_automation_event_outbox.sql").read_text(encoding="utf-8")
    assert "eyt_automation_events" in sql
    for table in ["sales_orders", "eyt_network_entities", "eyt_service_reminders"]:
        assert f"trg_eyt_automation_{table}" in sql
