#!/usr/bin/env python3
"""Guard the operational SQL baseline against duplicate Alembic DDL.

The repository uses the numbered SQL migrations as the runnable bootstrap
baseline while Alembic 0015+ is an extension segment for databases that
already contain the historical baseline. A later Alembic revision must not
recreate canonical tables that are already present in SQL migration 004.
"""

from __future__ import annotations

from pathlib import Path

BASELINE = Path("database/migrations/004_product_master_inventory.sql")
EXTENSION = Path("api/migrations/versions/0016_inventory_bom_reservation_costing.py")

CANONICAL_TABLES = ("inventory_transactions", "inventory_reservations")


def main() -> None:
    baseline = BASELINE.read_text(encoding="utf-8")
    extension = EXTENSION.read_text(encoding="utf-8")

    for table in CANONICAL_TABLES:
        if f"CREATE TABLE IF NOT EXISTS {table}" not in baseline:
            raise SystemExit(f"baseline does not define canonical table: {table}")
        if f'"{table}"' in extension and "op.create_table" in extension:
            raise SystemExit(f"Alembic 0016 must not recreate canonical table: {table}")

    for table in ("bom_versions", "bom_items", "production_costs"):
        if f'"{table}"' not in extension:
            raise SystemExit(f"Alembic 0016 missing expected extension table: {table}")

    print("Migration compatibility OK: Alembic 0016 extends, rather than duplicates, the SQL baseline")


if __name__ == "__main__":
    main()
