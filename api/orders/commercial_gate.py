from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

import psycopg


@dataclass(frozen=True)
class CommercialLine:
    product_id: str
    quantity: Decimal


class CommercialGate:
    """Read-only commercial validation before explicit customer confirmation.

    This layer never creates orders, reservations, production orders, or finance
    mutations. Final confirmation remains owned by OrderCenter's atomic path.
    """

    def __init__(self, connection_factory: Callable[[], Any] | None = None):
        self.connection_factory = connection_factory or self._default_connection

    @staticmethod
    def _default_connection():
        import os

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg.connect(database_url)

    @staticmethod
    def _money(value: Any) -> Decimal:
        return Decimal(str(value or 0))

    def evaluate(
        self,
        *,
        customer_id: str,
        warehouse_code: str,
        payment_type: str,
        items: tuple[CommercialLine, ...],
    ) -> dict[str, Any]:
        if not customer_id:
            raise ValueError("customer_id is required")
        if not warehouse_code:
            raise ValueError("warehouse_code is required")
        if not items:
            raise ValueError("at least one item is required")

        with self.connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, is_active FROM customers WHERE id=%s",
                (customer_id,),
            )
            customer = cur.fetchone()
            if not customer or not customer[2]:
                raise ValueError("active customer not found")

            cur.execute(
                "SELECT code FROM warehouses WHERE code=%s",
                (warehouse_code,),
            )
            if not cur.fetchone():
                raise ValueError(f"warehouse not found: {warehouse_code}")

            product_ids = [str(i.product_id) for i in items]
            values_sql = ",".join(["(%s::uuid,%s::numeric)"] * len(items))
            requested_params: list[Any] = []
            for item in items:
                requested_params.extend([str(item.product_id), item.quantity])

            cur.execute(
                f"""WITH requested(product_id, quantity) AS (VALUES {values_sql})
                    SELECT DISTINCT ON (r.product_id)
                           r.product_id, r.quantity,
                           p.product_code, p.sku, p.name_fa, p.sale_price,
                           p.purchase_price, p.is_active
                    FROM requested r
                    JOIN products p ON p.id=r.product_id
                    ORDER BY r.product_id""",
                requested_params,
            )
            products = {str(r[0]): r for r in cur.fetchall()}
            missing = [pid for pid in product_ids if pid not in products or not products[pid][7]]
            if missing:
                raise ValueError(f"active product not found: {', '.join(missing)}")

            # Match the canonical Order Center price precedence:
            # customer price list -> active price_master -> product sale_price.
            price_rows: dict[str, Decimal] = {}
            cur.execute(
                f"""WITH requested(product_id, quantity) AS (VALUES {values_sql})
                    SELECT DISTINCT ON (pli.product_id)
                           pli.product_id, pli.unit_price
                    FROM requested r
                    JOIN customers c ON c.id=%s
                    JOIN price_lists pl ON pl.id=c.default_price_list_id
                    JOIN price_list_items pli ON pli.price_list_id=pl.id
                      AND pli.product_id=r.product_id
                      AND pli.min_quantity<=r.quantity
                    WHERE pl.active=TRUE AND pli.active=TRUE
                      AND (pl.valid_to IS NULL OR pl.valid_to>CURRENT_TIMESTAMP)
                      AND (pli.valid_to IS NULL OR pli.valid_to>CURRENT_TIMESTAMP)
                      AND pli.valid_from<=CURRENT_TIMESTAMP
                    ORDER BY pli.product_id, pli.min_quantity DESC, pli.valid_from DESC""",
                [*requested_params, customer_id],
            )
            price_rows = {str(r[0]): self._money(r[1]) for r in cur.fetchall()}

            remaining = [pid for pid in product_ids if pid not in price_rows]
            master_rows: dict[str, Decimal] = {}
            if remaining:
                cur.execute(
                    """SELECT DISTINCT ON (product_id) product_id, final_price
                       FROM price_master
                       WHERE product_id=ANY(%s::uuid[]) AND status='ACTIVE'
                         AND effective_from<=CURRENT_TIMESTAMP
                         AND (effective_to IS NULL OR effective_to>CURRENT_TIMESTAMP)
                       ORDER BY product_id, effective_from DESC""",
                    (remaining,),
                )
                master_rows = {str(r[0]): self._money(r[1]) for r in cur.fetchall()}

            lines: list[dict[str, Any]] = []
            total = Decimal("0")
            for item in items:
                row = products[str(item.product_id)]
                price = price_rows.get(str(item.product_id))
                if price is None:
                    price = master_rows.get(str(item.product_id))
                if price is None:
                    price = self._money(row[5])
                if price <= 0:
                    raise ValueError(f"product has no valid sale price: {item.product_id}")

                cur.execute(
                    """SELECT COALESCE(SUM(CASE
                        WHEN transaction_type IN ('RECEIPT','PRODUCTION_RECEIPT','TRANSFER_IN','RETURN') THEN quantity
                        WHEN transaction_type IN ('ISSUE','TRANSFER_OUT','CONSUMPTION','SCRAP') THEN -quantity
                        ELSE 0 END),0)
                       FROM inventory_transactions
                       WHERE warehouse_code=%s
                         AND product_code=%s""",
                    (warehouse_code, row[2]),
                )
                physical = self._money(cur.fetchone()[0])
                cur.execute(
                    """SELECT COALESCE(SUM(quantity),0)
                       FROM inventory_reservations
                       WHERE warehouse_code=%s AND product_code=%s AND status='RESERVED'""",
                    (warehouse_code, row[2]),
                )
                reserved = self._money(cur.fetchone()[0])
                available = physical - reserved
                shortfall = max(item.quantity - available, Decimal("0"))
                line_total = item.quantity * price
                total += line_total
                lines.append({
                    "product_id": str(item.product_id),
                    "product_code": row[2],
                    "sku": row[3],
                    "name_fa": row[4],
                    "quantity": str(item.quantity),
                    "unit_price": str(price),
                    "line_total": str(line_total),
                    "physical_stock": str(physical),
                    "reserved_stock": str(reserved),
                    "available_stock": str(available),
                    "production_required": shortfall > 0,
                    "production_shortfall": str(shortfall),
                })

            credit = {
                "status": "NOT_REQUIRED",
                "credit_limit": None,
                "outstanding": None,
                "overdue": None,
                "available_credit": None,
                "requested_amount": str(total),
                "allowed": True,
                "reason": "CASH_PAYMENT",
            }
            if payment_type == "CREDIT":
                cur.execute(
                    """SELECT credit_limit, risk_level, manual_hold
                       FROM customer_credit_profiles WHERE customer_id=%s""",
                    (customer_id,),
                )
                profile = cur.fetchone()
                if not profile:
                    credit = {
                        **credit,
                        "status": "PROFILE_MISSING",
                        "allowed": False,
                        "reason": "CREDIT_PROFILE_NOT_FOUND",
                    }
                else:
                    cur.execute(
                        "SELECT COALESCE(SUM(outstanding),0) FROM receivables WHERE customer_id=%s",
                        (customer_id,),
                    )
                    outstanding = self._money(cur.fetchone()[0])
                    cur.execute(
                        """SELECT COALESCE(SUM(outstanding),0)
                           FROM receivables
                           WHERE customer_id=%s AND days_overdue > 0""",
                        (customer_id,),
                    )
                    overdue = self._money(cur.fetchone()[0])
                    limit = self._money(profile[0])
                    available_credit = max(limit - outstanding, Decimal("0"))
                    status = "OK"
                    if profile[2] or profile[1] == "BLOCKED":
                        status = "BLOCKED"
                    elif outstanding > limit:
                        status = "CREDIT_HOLD"
                    elif overdue > 0:
                        status = "REVIEW" if overdue < total else "HIGH_RISK"
                    allowed = status == "OK" and available_credit >= total
                    reason = "OK" if allowed else (
                        status if status != "OK" else "CREDIT_LIMIT_EXCEEDED"
                    )
                    credit = {
                        "status": status,
                        "risk_level": profile[1],
                        "manual_hold": bool(profile[2]),
                        "credit_limit": str(limit),
                        "outstanding": str(outstanding),
                        "overdue": str(overdue),
                        "available_credit": str(available_credit),
                        "requested_amount": str(total),
                        "allowed": allowed,
                        "reason": reason,
                    }

        stock_ok = all(not line["production_required"] for line in lines)
        credit_ok = bool(credit["allowed"])
        gate_status = "PASS" if stock_ok and credit_ok else "BLOCK"
        if credit_ok and not stock_ok:
            gate_status = "NEED_PRODUCTION"

        return {
            "gate_status": gate_status,
            "ready_for_confirmation": gate_status == "PASS",
            "customer": {
                "id": str(customer[0]),
                "name": customer[1],
            },
            "warehouse_code": warehouse_code,
            "payment_type": payment_type,
            "currency": "IRR",
            "items": lines,
            "totals": {
                "subtotal": str(total),
                "total": str(total),
            },
            "credit": credit,
            "delivery": {
                "status": "READY_FROM_STOCK" if stock_ok else "PRODUCTION_REQUIRED",
                "production_required": not stock_ok,
                "production_shortfall": str(sum(
                    (Decimal(line["production_shortfall"]) for line in lines),
                    Decimal("0"),
                )),
                "estimated_delivery_at": None,
            },
            "mutations_performed": False,
            "next_action": "CUSTOMER_CONFIRMATION" if gate_status == "PASS" else (
                "PRODUCTION_QUOTE_OR_DATE" if gate_status == "NEED_PRODUCTION" else "COMMERCIAL_REVIEW"
            ),
        }
