from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_network_crm_migration_registered():
    migration = ROOT / "database" / "migrations" / "038_network_crm_foundation.sql"
    runner = ROOT / "scripts" / "migrate_production.py"
    assert migration.exists()
    assert "038_network_crm_foundation.sql" in runner.read_text(encoding="utf-8")


def test_network_crm_api_mounted():
    main = (ROOT / "api" / "production" / "main.py").read_text(encoding="utf-8")
    assert "crm_network_router" in main
    api = ROOT / "api" / "production" / "crm_network_api.py"
    text = api.read_text(encoding="utf-8")
    assert "/api/v1/crm/network" in text
    assert "crm.read" in text
    assert "crm.write" in text


def test_channel_set_and_network_types_are_present():
    sql = (ROOT / "database" / "migrations" / "038_network_crm_foundation.sql").read_text(encoding="utf-8")
    for channel in ["TOROB", "DIGIKALA", "SNAPSHOP", "BASALAM", "WHATSAPP", "INSTAGRAM", "TELEGRAM", "SMS", "BALE", "RUBIKA"]:
        assert channel in sql
    for entity_type in ["CONSUMER", "MECHANIC", "RETAILER", "DISTRIBUTOR", "REPRESENTATIVE", "BRAND", "SUPPLIER", "FLEET"]:
        assert entity_type in sql
    for table in ["eyt_channel_identities", "eyt_marketing_consents", "eyt_network_relationships", "eyt_channel_attribution", "eyt_campaigns", "eyt_service_reminders"]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql


def test_network_crm_migration_uses_only_canonical_entity_backfills():
    sql = (ROOT / "database" / "migrations" / "038_network_crm_foundation.sql").read_text(encoding="utf-8")
    assert "customer_type" not in sql
    assert "FROM mechanics" not in sql
    assert "FROM parts_stores" not in sql
    assert "REFERENCES mechanics" not in sql
    assert "REFERENCES parts_stores" not in sql


def test_network_crm_graph_honors_depth_parameter():
    api = (ROOT / "api" / "production" / "crm_network_api.py").read_text(encoding="utf-8")
    assert "WITH RECURSIVE reachable" in api
    assert "reachable.depth < %s" in api
