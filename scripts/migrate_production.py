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
