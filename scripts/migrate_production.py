"""Apply the E.Y.T production post-init migration set safely.

The PostgreSQL Docker entrypoint runs migrations only when a database volume is
initialized for the first time. This runner is therefore used on every
production startup so an existing database also receives new idempotent
migrations. It intentionally targets migration 010, which is the current
master-data delta.
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database" / "migrations" / "010_eyt_master_data.sql"


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL must be set")
    if not MIGRATION.exists():
        raise SystemExit(f"Migration not found: {MIGRATION}")

    sql = MIGRATION.read_text(encoding="utf-8")
    with psycopg.connect(database_url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print(f"Applied/verified: {MIGRATION.name}")


if __name__ == "__main__":
    main()
