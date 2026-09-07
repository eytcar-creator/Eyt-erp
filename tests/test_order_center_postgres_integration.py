import os
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import psycopg

from api.orders.postgres_adapter import PostgresOrderRepository


pytestmark = __import__('pytest').mark.skipif(
    not os.getenv('DATABASE_URL'), reason='DATABASE_URL is required for PostgreSQL integration tests'
)


def connection_factory():
    return psycopg.connect(os.environ['DATABASE_URL'])


def seed_base():
    customer_id = uuid4()
    product_id = uuid4()
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO customers(id, customer_code, name) VALUES (%s,%s,%s)",
                (customer_id, f'T-CUST-{customer_id.hex[:8]}', 'Integration Customer'),
            )
            cur.execute(
                "INSERT INTO products(id, sku, product_code, name_fa, purchase_price, sale_price) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (product_id, f'T-SKU-{product_id.hex[:8]}', f'T-PROD-{product_id.hex[:8]}', 'Integration Product', 40, 100),
            )
            cur.execute(
                "INSERT INTO inventory_transactions(document_no, warehouse_code, product_code, quantity, transaction_type, unit_cost) "
                "VALUES (%s,%s,%s,%s,'RECEIPT',%s)",
                (f'T-RECEIPT-{product_id.hex[:8]}', 'MAIN', f'T-PROD-{product_id.hex[:8]}', 100, 40),
            )
        conn.commit()
    return customer_id, product_id, f'T-PROD-{product_id.hex[:8]}'


def test_order_center_atomic_postgres_flow_and_idempotency():
    customer_id, product_id, product_code = seed_base()
    repo = PostgresOrderRepository(connection_factory)
    key = f'test-{uuid4()}'
    order = SimpleNamespace(
        customer_id=str(customer_id),
        representative_id=None,
        warehouse_code='MAIN',
        channel=SimpleNamespace(value='RETAIL'),
        payment_type=SimpleNamespace(value='CASH'),
        idempotency_key=key,
        notes='integration',
        items=(SimpleNamespace(product_id=str(product_id), quantity=Decimal('10'), unit_price=Decimal('100')) ,),
    )

    first = repo.create(order)
    second = repo.create(order)
    assert first['order_no'] == second['order_no']

    result = repo.confirm_with_controls(
        first['order_no'], str(customer_id), 'MAIN', 'CASH', order.items
    )
    assert result['status'] == 'RESERVED'

    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, cost_snapshot, contribution FROM sales_order_items "
                "WHERE sales_order_id=(SELECT id FROM sales_orders WHERE order_no=%s)",
                (first['order_no'],),
            )
            row = cur.fetchone()
            assert row[0] is not None
            assert Decimal(str(row[1])) == Decimal('40')
            assert Decimal(str(row[2])) == Decimal('600')

            cur.execute(
                "SELECT quantity FROM inventory_reservations WHERE document_no=%s",
                (first['order_no'],),
            )
            assert Decimal(str(cur.fetchone()[0])) == Decimal('10')

            cur.execute(
                "SELECT COUNT(*) FROM order_audit_log WHERE order_no=%s AND event_type=%s",
                (first['order_no'], 'ORDER_CONFIRMED_AND_RESERVED'),
            )
            assert cur.fetchone()[0] == 1

            cur.execute(
                "SELECT COUNT(*) FROM sales_orders WHERE idempotency_key=%s",
                (key,),
            )
            assert cur.fetchone()[0] == 1


def test_insufficient_stock_rolls_back_order_confirmation():
    customer_id, product_id, _ = seed_base()
    repo = PostgresOrderRepository(connection_factory)
    order = SimpleNamespace(
        customer_id=str(customer_id),
        representative_id=None,
        warehouse_code='MAIN',
        channel=SimpleNamespace(value='RETAIL'),
        payment_type=SimpleNamespace(value='CASH'),
        idempotency_key=f'test-{uuid4()}',
        notes=None,
        items=(SimpleNamespace(product_id=str(product_id), quantity=Decimal('101'), unit_price=Decimal('100')) ,),
    )
    created = repo.create(order)

    try:
        repo.confirm_with_controls(created['order_no'], str(customer_id), 'MAIN', 'CASH', order.items)
        assert False, 'expected insufficient stock failure'
    except ValueError as exc:
        assert 'insufficient stock' in str(exc)

    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM sales_orders WHERE order_no=%s", (created['order_no'],))
            assert cur.fetchone()[0] == 'PENDING_CONFIRMATION'
            cur.execute("SELECT COUNT(*) FROM inventory_reservations WHERE document_no=%s", (created['order_no'],))
            assert cur.fetchone()[0] == 0


def test_credit_hold_rolls_back_before_stock_reservation():
    customer_id, product_id, _ = seed_base()
    repo = PostgresOrderRepository(connection_factory)
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO customer_credit_profiles(customer_id, credit_limit, risk_level, manual_hold) "
                "VALUES (%s,%s,%s,%s)",
                (customer_id, 10000, 'BLOCKED', True),
            )
        conn.commit()

    order = SimpleNamespace(
        customer_id=str(customer_id),
        representative_id=None,
        warehouse_code='MAIN',
        channel=SimpleNamespace(value='RETAIL'),
        payment_type=SimpleNamespace(value='CREDIT'),
        idempotency_key=f'test-{uuid4()}',
        notes=None,
        items=(SimpleNamespace(product_id=str(product_id), quantity=Decimal('1'), unit_price=Decimal('100')) ,),
    )
    created = repo.create(order)

    try:
        repo.confirm_with_controls(created['order_no'], str(customer_id), 'MAIN', 'CREDIT', order.items)
        assert False, 'expected credit hold failure'
    except ValueError as exc:
        assert 'credit check failed' in str(exc)

    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM sales_orders WHERE order_no=%s", (created['order_no'],))
            assert cur.fetchone()[0] == 'PENDING_CONFIRMATION'
            cur.execute("SELECT COUNT(*) FROM inventory_reservations WHERE document_no=%s", (created['order_no'],))
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT allowed FROM order_credit_checks WHERE order_no=%s ORDER BY id DESC LIMIT 1", (created['order_no'],))
            assert cur.fetchone()[0] is False
