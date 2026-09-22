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


def test_automation_permissions_are_seeded():
    sql = (ROOT / "database" / "migrations" / "039_automation_event_outbox.sql").read_text(encoding="utf-8")
    assert "automation.read" in sql
    assert "automation.write" in sql
    assert "WHERE r.name='CEO'" in sql


def test_automation_api_claims_events_atomically():
    api = (ROOT / "api" / "production" / "automation_api.py").read_text(encoding="utf-8")
    assert '"/events/claim"' in api
    assert "FOR UPDATE SKIP LOCKED" in api
    assert "status='PROCESSING'" in api


def test_automation_effect_idempotency_contract():
    migration = ROOT / "database" / "migrations" / "040_automation_effect_idempotency.sql"
    assert migration.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "eyt_automation_effects" in sql
    assert "idempotency_key VARCHAR(300) NOT NULL UNIQUE" in sql
    assert "event_id UUID REFERENCES eyt_automation_events" in sql


def test_automation_effect_api_contract():
    api = (ROOT / "api" / "production" / "automation_api.py").read_text(encoding="utf-8")
    assert '"/effects/reserve"' in api
    assert '"/effects/{effect_id}/complete"' in api
    assert '"/effects/{effect_id}/fail"' in api
    assert "ON CONFLICT (idempotency_key) DO NOTHING" in api
    assert '"should_send": created' in api


def test_automation_effect_migration_is_registered():
    runner = (ROOT / "scripts" / "migrate_production.py").read_text(encoding="utf-8")
    assert "040_automation_effect_idempotency.sql" in runner
