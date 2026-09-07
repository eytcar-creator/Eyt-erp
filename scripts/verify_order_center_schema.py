"""Integration smoke test for the PostgreSQL Order Center schema contract."""
import os
import sys

import psycopg


def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            required = {
                "products": {"product_code", "purchase_price"},
                "warehouses": {"code"},
                "receivables": {"outstanding", "days_overdue"},
                "sales_orders": {
                    "representative_id", "channel", "payment_type", "idempotency_key",
                    "notes", "confirmed_at", "updated_at",
                },
                "sales_order_items": {"cost_snapshot", "contribution"},
                "inventory_reservations": {
                    "document_no", "warehouse_code", "product_code", "quantity", "status",
                },
                "customer_credit_profiles": {"customer_id", "credit_limit", "risk_level", "manual_hold"},
                "order_credit_checks": {
                    "order_no", "customer_id", "requested_amount", "allowed",
                    "credit_status", "available_credit",
                },
                "order_audit_log": {"order_no", "event_type"},
                "representatives": {"id", "representative_code", "name", "active"},
            }
            for table, columns in required.items():
                cur.execute(
                    """SELECT column_name FROM information_schema.columns
                       WHERE table_schema='public' AND table_name=%s""",
                    (table,),
                )
                actual = {row[0] for row in cur.fetchall()}
                missing = columns - actual
                if missing:
                    raise AssertionError(f"{table}: missing columns {sorted(missing)}")

            cur.execute("SELECT to_regclass('public.representatives')")
            if cur.fetchone()[0] != "representatives":
                raise AssertionError("representatives table is missing")

    print("Order Center PostgreSQL schema contract: PASS")


if __name__ == "__main__":
    main()
