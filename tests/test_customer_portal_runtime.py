"""Database-backed integration test template for the customer portal.

Skipped unless EYT_RUN_DB_TESTS=1 and DATABASE_URL are configured. This keeps
normal CI deterministic while providing a ready boundary for staging tests.
"""
import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("EYT_RUN_DB_TESTS") != "1" or not os.getenv("DATABASE_URL"),
    reason="requires EYT_RUN_DB_TESTS=1 and DATABASE_URL",
)


def test_staging_database_is_configured():
    import psycopg

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchone() == (1,)


def test_customer_portal_tables_exist():
    import psycopg

    required = {
        "customers",
        "customer_accounts",
        "customer_account_sessions",
        "price_lists",
        "price_list_items",
        "sales_orders",
        "sales_order_items",
    }
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name = ANY(%s)",
                (list(required),),
            )
            found = {r[0] for r in cur.fetchall()}
    assert required <= found
