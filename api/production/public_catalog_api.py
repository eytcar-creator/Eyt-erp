from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException, Query
import psycopg

router = APIRouter(prefix="/api/public/catalog", tags=["public-catalog"])

def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return psycopg.connect(url)

@router.get("/products")
def list_public_products(q: str | None = Query(default=None, max_length=150),
                         make: str | None = Query(default=None, max_length=100),
                         model: str | None = Query(default=None, max_length=150),
                         limit: int = Query(default=50, ge=1, le=200)):
    with _connect() as conn, conn.cursor() as cur:
        where = ["p.status = 'ACTIVE'"]
        params = []
        if q:
            term = f"%{q}%"
            where.append("(p.sku ILIKE %s OR p.product_name_fa ILIKE %s OR p.product_name_en ILIKE %s OR p.code128 ILIKE %s)")
            params.extend([term] * 4)
        if make:
            where.append("EXISTS (SELECT 1 FROM eyt_product_vehicle_fitment f JOIN eyt_vehicle_master v ON v.id=f.vehicle_id WHERE f.product_id=p.id AND v.make ILIKE %s AND f.status='ACTIVE')")
            params.append(make)
        if model:
            where.append("EXISTS (SELECT 1 FROM eyt_product_vehicle_fitment f JOIN eyt_vehicle_master v ON v.id=f.vehicle_id WHERE f.product_id=p.id AND v.model ILIKE %s AND f.status='ACTIVE')")
            params.append(model)
        cur.execute(f"""SELECT p.id,p.sku,p.code128,p.product_name_fa,p.product_name_en,
                               p.product_type,p.category,p.brand,p.unit,p.status,p.description,
                               p.retail_price,p.distribution_price,p.wholesale_price,p.attributes
                        FROM eyt_product_master p
                        WHERE {' AND '.join(where)}
                        ORDER BY p.product_name_fa,p.sku LIMIT %s""", [*params, limit])
        rows = cur.fetchall()
        columns = [d.name for d in cur.description]
        result = []
        for row in rows:
            item = dict(zip(columns, row))
            cur.execute("""SELECT v.make,v.model,v.generation,v.trim,v.model_year_from,
                                  v.model_year_to,v.engine,v.transmission,f.position,
                                  f.fitment_note,f.oe_numbers
                           FROM eyt_product_vehicle_fitment f
                           JOIN eyt_vehicle_master v ON v.id=f.vehicle_id
                           WHERE f.product_id=%s AND f.status='ACTIVE' AND v.status='ACTIVE'
                           ORDER BY v.make,v.model,v.model_year_from NULLS FIRST""", (item["id"],))
            fitment_rows = cur.fetchall()
            fitment_columns = [d.name for d in cur.description]
            item["fitments"] = [dict(zip(fitment_columns, r)) for r in fitment_rows]
            item["id"] = str(item["id"])
            result.append(item)
    return {"count": len(result), "items": result}

@router.get("/products/{sku}")
def get_public_product(sku: str):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT id,sku,code128,product_name_fa,product_name_en,product_type,
                              category,brand,unit,status,description,retail_price,
                              distribution_price,wholesale_price,attributes
                       FROM eyt_product_master WHERE sku=%s AND status='ACTIVE'""", (sku,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Catalog product not found")
        columns = [d.name for d in cur.description]
        item = dict(zip(columns, row))
        cur.execute("""SELECT v.make,v.model,v.generation,v.trim,v.model_year_from,
                              v.model_year_to,v.engine,v.transmission,f.position,
                              f.fitment_note,f.oe_numbers
                       FROM eyt_product_vehicle_fitment f
                       JOIN eyt_vehicle_master v ON v.id=f.vehicle_id
                       WHERE f.product_id=%s AND f.status='ACTIVE' AND v.status='ACTIVE'
                       ORDER BY v.make,v.model,v.model_year_from NULLS FIRST""", (item["id"],))
        fitment_rows = cur.fetchall()
        fitment_columns = [d.name for d in cur.description]
    item["id"] = str(item["id"])
    item["fitments"] = [dict(zip(fitment_columns, r)) for r in fitment_rows]
    return item
