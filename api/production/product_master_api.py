from __future__ import annotations

from decimal import Decimal
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from .auth import audit, require_permission

router = APIRouter(prefix="/api/products", tags=["product-master"])


class ProductInput(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    productCode: str = Field(min_length=1, max_length=100)
    nameFa: str = Field(min_length=1, max_length=255)
    nameEn: str | None = Field(default=None, max_length=255)
    categoryCode: str | None = Field(default=None, max_length=60)
    productType: str = Field(default="FINISHED_GOOD", max_length=40)
    brand: str = Field(default="E.Y.T", max_length=100)
    unit: str = Field(default="PCS", max_length=20)
    barcode: str | None = Field(default=None, max_length=100)
    oemCode: str | None = Field(default=None, max_length=150)
    specification: str | None = Field(default=None, max_length=500)
    weightKg: Decimal | None = Field(default=None, ge=0)
    purchasePrice: Decimal = Field(default=Decimal("0"), ge=0)
    salePrice: Decimal = Field(default=Decimal("0"), ge=0)
    reorderPoint: Decimal = Field(default=Decimal("0"), ge=0)
    minStock: Decimal = Field(default=Decimal("0"), ge=0)
    maxStock: Decimal = Field(default=Decimal("0"), ge=0)


class FitmentInput(BaseModel):
    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=150)
    trim: str | None = Field(default=None, max_length=150)
    yearFrom: int | None = None
    yearTo: int | None = None
    notes: str | None = None


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


def _product_row(cur, product_code: str):
    cur.execute("""SELECT p.id,p.sku,p.product_code,p.name_fa,p.name_en,p.product_type,p.brand,p.unit,
                          p.barcode,p.oem_code,p.specification,p.weight_kg,p.purchase_price,p.sale_price,
                          p.reorder_point,p.min_stock,p.max_stock,p.is_active,c.code,c.name_fa
                   FROM products p LEFT JOIN product_categories c ON c.id=p.category_id
                   WHERE p.product_code=%s""", (product_code,))
    return cur.fetchone()


def _dump(row):
    if row is None:
        return None
    keys = ["id","sku","productCode","nameFa","nameEn","productType","brand","unit","barcode","oemCode",
            "specification","weightKg","purchasePrice","salePrice","reorderPoint","minStock","maxStock",
            "isActive","categoryCode","categoryNameFa"]
    return dict(zip(keys, row))


@router.post("", status_code=201)
def create_product(payload: ProductInput, request: Request, principal: dict = Depends(require_permission("product.write"))):
    with _connect() as conn, conn.cursor() as cur:
        category_id = None
        if payload.categoryCode:
            cur.execute("SELECT id FROM product_categories WHERE code=%s AND is_active", (payload.categoryCode,))
            category = cur.fetchone()
            if category is None:
                raise HTTPException(422, "Unknown or inactive category")
            category_id = category[0]
        try:
            cur.execute("""INSERT INTO products
                (sku,product_code,name_fa,name_en,category_id,product_type,brand,unit,barcode,oem_code,
                 specification,weight_kg,purchase_price,sale_price,reorder_point,min_stock,max_stock)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id""", (payload.sku,payload.productCode,payload.nameFa,payload.nameEn,category_id,
                payload.productType,payload.brand,payload.unit,payload.barcode,payload.oemCode,payload.specification,
                payload.weightKg,payload.purchasePrice,payload.salePrice,payload.reorderPoint,payload.minStock,payload.maxStock))
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(409, "SKU, product code, or barcode already exists") from exc
        product_id = cur.fetchone()[0]
    audit(request, principal, "product.create", product_id, {"product_code": payload.productCode, "sku": payload.sku})
    return {"id": product_id, "sku": payload.sku, "productCode": payload.productCode, "status": "active"}


@router.get("")
def list_products(q: str | None = Query(default=None, max_length=150), active_only: bool = True,
                  _=Depends(require_permission("product.read"))):
    with _connect() as conn, conn.cursor() as cur:
        where = ["p.is_active = TRUE"] if active_only else []
        params = []
        if q:
            where.append("(p.sku ILIKE %s OR p.product_code ILIKE %s OR p.name_fa ILIKE %s OR p.name_en ILIKE %s OR p.oem_code ILIKE %s)")
            term = f"%{q}%"
            params.extend([term] * 5)
        clause = " WHERE " + " AND ".join(where) if where else ""
        cur.execute(f"""SELECT p.id,p.sku,p.product_code,p.name_fa,p.name_en,p.product_type,p.brand,p.unit,p.barcode,p.oem_code,
                               p.specification,p.weight_kg,p.purchase_price,p.sale_price,p.reorder_point,p.min_stock,p.max_stock,
                               p.is_active,c.code,c.name_fa
                        FROM products p LEFT JOIN product_categories c ON c.id=p.category_id{clause}
                        ORDER BY p.product_code LIMIT 200""", params)
        return [_dump(row) for row in cur.fetchall()]


@router.get("/{product_code}")
def get_product(product_code: str, _=Depends(require_permission("product.read"))):
    with _connect() as conn, conn.cursor() as cur:
        product = _dump(_product_row(cur, product_code))
        if product is None:
            raise HTTPException(404, "Product not found")
        cur.execute("SELECT make,model,trim,year_from,year_to,notes FROM product_vehicle_fitments WHERE product_id=%s ORDER BY make,model", (product["id"],))
        product["fitments"] = [dict(zip(["make","model","trim","yearFrom","yearTo","notes"], row)) for row in cur.fetchall()]
        cur.execute("SELECT alias,alias_type FROM product_aliases WHERE product_id=%s ORDER BY alias", (product["id"],))
        product["aliases"] = [{"alias": row[0], "aliasType": row[1]} for row in cur.fetchall()]
    return product


@router.post("/{product_code}/fitments", status_code=201)
def add_fitment(product_code: str, payload: FitmentInput, request: Request,
                principal: dict = Depends(require_permission("product.write"))):
    if payload.yearFrom and payload.yearTo and payload.yearTo < payload.yearFrom:
        raise HTTPException(422, "yearTo must be greater than or equal to yearFrom")
    with _connect() as conn, conn.cursor() as cur:
        product = _product_row(cur, product_code)
        if product is None:
            raise HTTPException(404, "Product not found")
        try:
            cur.execute("""INSERT INTO product_vehicle_fitments(product_id,make,model,trim,year_from,year_to,notes)
                           VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (product[0],payload.make,payload.model,payload.trim,payload.yearFrom,payload.yearTo,payload.notes))
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(409, "Vehicle fitment already exists") from exc
        fitment_id = cur.fetchone()[0]
    audit(request, principal, "product.fitment.add", product[0], {"fitment_id": fitment_id, "make": payload.make, "model": payload.model})
    return {"id": fitment_id, "productCode": product_code, **payload.model_dump()}
