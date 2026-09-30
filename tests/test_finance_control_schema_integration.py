import os

import pytest


pytestmark = pytest.mark.integration


REQUIRED_TABLES = {
    "finance_funding_sources",
    "finance_cash_movements",
    "finance_alerts",
    "finance_settlement_alerts",
    "finance_notification_outbox",
}

REQUIRED_COLUMNS = {
    "payments": {"funding_source_id"},
    "production_payments": {"funding_source_id"},
    "invoices": {"due_at"},
    "finance_notification_outbox": {"processing_started_at", "locked_by"},
}


def _connect():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not configured")

    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(database_url)


def test_finance_control_schema_is_present():
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                """,
                (list(REQUIRED_TABLES),),
            )
            actual_tables = {row[0] for row in cur.fetchall()}

            assert actual_tables == REQUIRED_TABLES

            for table_name, columns in REQUIRED_COLUMNS.items():
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = %s
                      AND column_name = ANY(%s)
                    """,
                    (table_name, list(columns)),
                )
                actual_columns = {row[0] for row in cur.fetchall()}
                assert actual_columns == columns, table_name
