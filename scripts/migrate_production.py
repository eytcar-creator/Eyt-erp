"""Apply upgrade-only E.Y.T production migrations safely.

A brand-new PostgreSQL volume already receives the complete migration directory
through the Docker entrypoint. This runner is for existing volumes only, so it
must not replay the foundational schema and risk changing live constraints.

Only migrations introduced after the original production bootstrap are checked
and applied here. Every migration remains idempotent.
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]

# These are the migrations that belong to the original/bootstrap path. They are
# intentionally listed for contract/audit visibility but are NOT executed here.
# A new PostgreSQL volume receives them through docker-entrypoint-initdb.d.
BOOTSTRAP_MIGRATION_NAMES = [
    "011_order_center_atomic.sql",
    "018_order_center_schema_contract.sql",
    "20260904_inventory_transactions.sql",
    "20260908_production_control_hardening.sql",
    "20260908_production_inventory_wip.sql",
    "20260908_production_payments.sql",
    "029_eyt_core_master_v1.sql",
    "030_eyt_bom_routing_cost_engine_v1.sql",
    "031_eyt_material_consumption_v1.sql",
    "032_eyt_actual_cost_v1.sql",
    "033_eyt_profit_actual_cost_link_v1.sql",
    "034_eyt_ceo_dashboard_actual_profit.sql",
    "035_deep_smoke_hardening.sql",
    "036_eyt_actual_cost_order_bridge.sql",
    "037_ceo_dashboard_finance_permission.sql",
    "038_network_crm_foundation.sql",
    "039_automation_event_outbox.sql",
    "040_automation_effect_idempotency.sql",
    "041_crm_activity.sql",
    "20260930_finance_cash_control_v1.sql",
    "20260930_finance_settlement_bridge_v1.sql",
    "20260930_finance_settlement_alerts_v1.sql",
    "20260930_finance_due_and_notification_outbox_v1.sql",
    "20260930_finance_notification_worker_hardening_v1.sql",
    "20261001_inventory_unit_type_hardening.sql",
    "20261001z_inventory_unit_contract_v2.sql",
]

UPGRADES = [
    ROOT / "database" / "migrations" / "042_eyt_one_channel_intake.sql",
    ROOT / "database" / "migrations" / "043_eyt_one_customer_confirmation.sql",
    ROOT / "database" / "migrations" / "045_price_master_contract.sql",
]


def _table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
    return cur.fetchone()[0] is not None


def _column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.columns
          WHERE table_schema='public'
            AND table_name=%s
            AND column_name=%s
        )
        """,
        (table_name, column_name),
    )
    return bool(cur.fetchone()[0])


def _should_apply(cur, migration: Path) -> bool:
    if migration.name == "042_eyt_one_channel_intake.sql":
        return not _table_exists(cur, "channel_intakes")
    if migration.name == "043_eyt_one_customer_confirmation.sql":
        return _table_exists(cur, "channel_intakes") and not _column_exists(
            cur, "channel_intakes", "proposal_fingerprint"
        )
    if migration.name == "045_price_master_contract.sql":
        return not _table_exists(cur, "price_master")
    return False


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL must be set")

    missing = [str(path) for path in UPGRADES if not path.exists()]
    if missing:
        raise SystemExit(f"Migrations not found: {', '.join(missing)}")

    with psycopg.connect(database_url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            for migration in UPGRADES:
                if not _should_apply(cur, migration):
                    print(f"Already present/verified: {migration.name}")
                    continue
                cur.execute(migration.read_text(encoding="utf-8"))
                print(f"Applied/verified: {migration.name}")
        conn.commit()


if __name__ == "__main__":
    main()
