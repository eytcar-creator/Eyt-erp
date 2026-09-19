"""Apply the E.Y.T production migration set on every startup.

The Docker PostgreSQL entrypoint applies the full migration directory on a
brand-new volume. The explicit runner below is intentionally limited to the
post-init/upgrade migrations that must also reach existing production volumes.
All entries must remain idempotent.
"""
from __future__ import annotations

import os
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = [
    ROOT / "database" / "migrations" / "011_order_center_atomic.sql",
    ROOT / "database" / "migrations" / "018_order_center_schema_contract.sql",
    ROOT / "database" / "migrations" / "20260904_inventory_transactions.sql",
    ROOT / "database" / "migrations" / "20260908_production_control_hardening.sql",
    ROOT / "database" / "migrations" / "20260908_production_inventory_wip.sql",
    ROOT / "database" / "migrations" / "20260908_production_payments.sql",
    ROOT / "database" / "migrations" / "029_eyt_core_master_v1.sql",
    ROOT / "database" / "migrations" / "030_eyt_bom_routing_cost_engine_v1.sql",
    ROOT / "database" / "migrations" / "031_eyt_material_consumption_v1.sql",
    ROOT / "database" / "migrations" / "032_eyt_actual_cost_v1.sql",
    ROOT / "database" / "migrations" / "033_eyt_profit_actual_cost_link_v1.sql",
    ROOT / "database" / "migrations" / "034_eyt_ceo_dashboard_actual_profit.sql",
    ROOT / "database" / "migrations" / "035_deep_smoke_hardening.sql",
]

def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL must be set")
    missing = [str(path) for path in MIGRATIONS if not path.exists()]
    if missing:
        raise SystemExit(f"Migrations not found: {', '.join(missing)}")
    with psycopg.connect(database_url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            for migration in MIGRATIONS:
                cur.execute(migration.read_text(encoding="utf-8"))
                print(f"Applied/verified: {migration.name}")
        conn.commit()

if __name__ == "__main__":
    main()
