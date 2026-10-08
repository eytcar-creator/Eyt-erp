from __future__ import annotations

import os
import re
from typing import Any

import psycopg


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)


def _norm(value: str | None) -> str:
    value = value or ""
    value = value.translate(str.maketrans("يىكۀة","ییکهه"))
    value = value.lower().strip()
    return re.sub(r"[^\w\u0600-\u06ff]+", "", value, flags=re.UNICODE)


def _candidate(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = ("id", "code", "name", "phone", "city")
    return {k: (str(v) if k == "id" and v is not None else v) for k, v in zip(keys, row)}


class ResolutionService:
    """Read-only resolver over the existing Customer/Product Master data."""

    def resolve_customer(
        self,
        customer_id: str | None = None,
        customer_code: str | None = None,
        phone: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        with _connect() as conn, conn.cursor() as cur:
            if customer_id:
                cur.execute(
                    "SELECT id,customer_code,name,phone,city FROM customers WHERE id=%s AND is_active",
                    (customer_id,),
                )
                row = cur.fetchone()
                if row:
                    return {"status": "EXACT", "confidence": 1.0, "source": "customer_id", "customer": _candidate(row)}

            for field, value in (("customer_code", customer_code), ("phone", phone)):
                if not value:
                    continue
                cur.execute(
                    f"SELECT id,customer_code,name,phone,city FROM customers WHERE {field}=%s AND is_active LIMIT 10",
                    (value.strip(),),
                )
                rows = cur.fetchall()
                if len(rows) == 1:
                    return {"status": "EXACT", "confidence": 0.99, "source": field, "customer": _candidate(rows[0])}
                if len(rows) > 1:
                    return {"status": "AMBIGUOUS", "confidence": 0.55, "source": field, "candidates": [_candidate(r) for r in rows]}

            if name:
                needle = _norm(name)
                if needle:
                    cur.execute(
                        """SELECT id,customer_code,name,phone,city
                           FROM customers
                           WHERE is_active AND regexp_replace(lower(translate(name,'يىكۀة','ییکهه')),'[^[:alnum:]\u0600-\u06ff]','','g')=%s
                           LIMIT 10""",
                        (needle,),
                    )
                    rows = cur.fetchall()
                    if len(rows) == 1:
                        return {"status": "EXACT", "confidence": 0.93, "source": "normalized_name", "customer": _candidate(rows[0])}
                    if rows:
                        return {"status": "AMBIGUOUS", "confidence": 0.60, "source": "normalized_name", "candidates": [_candidate(r) for r in rows]}

        return {"status": "NOT_FOUND", "confidence": 0.0, "source": None, "candidates": []}

    def resolve_product(
        self,
        identifier: str | None = None,
        name: str | None = None,
        vehicle_make: str | None = None,
        vehicle_model: str | None = None,
    ) -> dict[str, Any]:
        with _connect() as conn, conn.cursor() as cur:
            if identifier:
                cur.execute(
                    """SELECT id,sku,product_code,name_fa,name_en,barcode,oem_code
                       FROM products WHERE is_active AND
                       (product_code=%s OR sku=%s OR barcode=%s OR oem_code=%s)
                       LIMIT 10""",
                    (identifier, identifier, identifier, identifier),
                )
                rows = cur.fetchall()
                if len(rows) == 1:
                    return {"status": "EXACT", "confidence": 1.0, "source": "product_identifier", "product": self._product(rows[0])}
                if len(rows) > 1:
                    return {"status": "AMBIGUOUS", "confidence": 0.65, "source": "product_identifier", "candidates": [self._product(r) for r in rows]}

            if name:
                needle = name.strip()
                if needle:
                    params: list[Any] = [f"%{needle}%", f"%{needle}%", f"%{needle}%"]
                    sql = """SELECT DISTINCT p.id,p.sku,p.product_code,p.name_fa,p.name_en,p.barcode,p.oem_code
                             FROM products p
                             LEFT JOIN product_aliases pa ON pa.product_id=p.id
                             WHERE p.is_active
                               AND (p.name_fa ILIKE %s OR p.name_en ILIKE %s OR pa.alias ILIKE %s)"""
                    if vehicle_make or vehicle_model:
                        sql += """ AND EXISTS (
                            SELECT 1 FROM product_vehicle_fitments f
                            WHERE f.product_id=p.id
                              AND (%s='' OR f.make ILIKE %s)
                              AND (%s='' OR f.model ILIKE %s)
                        )"""
                        make = vehicle_make or ""
                        model = vehicle_model or ""
                        params.extend([make, f"%{make}%", model, f"%{model}%"])
                    sql += " ORDER BY p.product_code LIMIT 20"
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    if len(rows) == 1:
                        return {"status": "EXACT", "confidence": 0.90, "source": "name_alias_fitment", "product": self._product(rows[0])}
                    if rows:
                        return {"status": "AMBIGUOUS", "confidence": 0.62, "source": "name_alias_fitment", "candidates": [self._product(r) for r in rows]}

        return {"status": "NOT_FOUND", "confidence": 0.0, "source": None, "candidates": []}

    @staticmethod
    def _product(row: tuple[Any, ...]) -> dict[str, Any]:
        keys = ("id", "sku", "product_code", "name_fa", "name_en", "barcode", "oem_code")
        return {k: (str(v) if k == "id" and v is not None else v) for k, v in zip(keys, row)}
