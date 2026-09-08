"""Apply the E.Y.T production post-init migration set safely.

The PostgreSQL Docker entrypoint runs migrations only when a database volume is
initialized for the first time. This runner is therefore used on every
production startup so an existing database also receives the current
idempotent post-init migrations.
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
