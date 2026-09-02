from __future__ import annotations

import os

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .auth import audit, require_permission

router = APIRouter(prefix="/api/v1", tags=["E.Y.T master data"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


class VehicleInput(BaseModel):
    vehicleId: str = Field(min_length=1, max_length=60)
    brandId: str = Field(min_length=1, max_length=60)
    brandName: str = Field(min_length=1, max_length=100)
    modelId: str = Field(min_length=1, max_length=100)
    modelName: str = Field(min_length=1, max_length=150)
    generation: str | None = None
    platform: str | None = None
    bodyType: str | None = None
    market: str = "Iran"
    engineCode: str | None = None
    displacement: str | None = None
    transmissionType: str | None = None
    driveType: str | None = None
    modelYear: str | None = None
    notes: str | None = None


class CompatibilityInput(BaseModel):
    productCode: str
    vehicleId: str
    fitmentStatus: str = "UNDER_REVIEW"
    position: str | None = None
    side: str | None = None
    engineCode: str | None = None
    engineVolume: str | None = None
    transmission: str | None = None
    yearFrom: int | None = None
    yearTo: int | None = None
    oemReference: str | None = None
    fitmentConfidence: str = "UNDER_REVIEW"
    notes: str | None = None


@router.get("/catalog/vehicles")
def catalog_vehicles(q: str | None = Query(default=None, max_length=100)):
    """Public catalog vehicle list. Only active master records are exposed."""
    with _connect() as conn, conn.cursor() as cur:
        if q:
            term = f"%{q}%"
            cur.execute(
                """SELECT vehicle_id, brand_id, brand_name, model_id, model_name, body_type, market,
                          generation, platform, displacement, model_year
                   FROM vehicle_master
                   WHERE is_active AND (brand_name ILIKE %s OR model_name ILIKE %s OR vehicle_id ILIKE %s)
                   ORDER BY brand_name, model_name""", (term, term, term))
        else:
            cur.execute(
                """SELECT vehicle_id, brand_id, brand_name, model_id, model_name, body_type, market,
                          generation, platform, displacement, model_year
                   FROM vehicle_master WHERE is_active ORDER BY brand_name, model_name"""
            )
        keys = ["vehicleId", "brandId", "brandName", "modelId", "modelName", "bodyType", "market",
                "generation", "platform", "displacement", "modelYear"]
        return [dict(zip(keys, row)) for row in cur.fetchall()]


@router.get("/catalog/vehicles/{vehicle_id}/products")
def catalog_vehicle_products(vehicle_id: str):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM vehicle_master WHERE vehicle_id=%s AND is_active", (vehicle_id,))
        vehicle = cur.fetchone()
        if vehicle is None:
            raise HTTPException(404, "Vehicle not found")
        cur.execute(
            """SELECT p.product_code,p.sku,p.name_fa,p.name_en,p.product_type,p.unit,p.barcode,p.oem_code,
                      p.specification,c.code,c.name_fa,pc.position,pc.side,pc.year_from,pc.year_to
               FROM product_vehicle_compatibility pc JOIN products p ON p.id=pc.product_id
               LEFT JOIN product_categories c ON c.id=p.category_id
               WHERE pc.vehicle_id=%s AND pc.is_active AND pc.fitment_status='CONFIRMED'
                 AND pc.fitment_confidence='CONFIRMED' AND p.is_active
               ORDER BY c.code,p.name_fa""", (vehicle[0],))
        keys = ["productCode", "sku", "nameFa", "nameEn", "productType", "unit", "barcode", "oemCode",
                "specification", "categoryCode", "categoryNameFa", "position", "side", "yearFrom", "yearTo"]
        return [dict(zip(keys, row)) for row in cur.fetchall()]


@router.get("/catalog/vehicles/{vehicle_id}/kits")
def catalog_vehicle_kits(vehicle_id: str):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM vehicle_master WHERE vehicle_id=%s AND is_active", (vehicle_id,))
        vehicle = cur.fetchone()
        if vehicle is None:
            raise HTTPException(404, "Vehicle not found")
        cur.execute(
            """SELECT DISTINCT p.product_code,p.sku,p.name_fa,p.name_en,p.product_type
               FROM product_vehicle_compatibility pc JOIN products p ON p.id=pc.product_id
               WHERE pc.vehicle_id=%s AND pc.is_active AND pc.fitment_status='CONFIRMED'
                 AND pc.fitment_confidence='CONFIRMED' AND p.is_active AND p.product_type IN ('KIT','PACK')
               ORDER BY p.name_fa""", (vehicle[0],))
        keys = ["productCode", "sku", "nameFa", "nameEn", "productType"]
        return [dict(zip(keys, row)) for row in cur.fetchall()]


@router.get("/catalog/products/{product_code}/bom")
def catalog_product_bom(product_code: str):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM products WHERE product_code=%s AND is_active", (product_code,))
        parent = cur.fetchone()
        if parent is None:
            raise HTTPException(404, "Product not found")
        cur.execute(
            """SELECT c.product_code,c.sku,c.name_fa,c.name_en,b.quantity,b.unit,b.required,b.loss_percent,
                      b.assembly_sequence,b.qc_required
               FROM kit_bom_master b JOIN products c ON c.id=b.component_product_id
               WHERE b.parent_product_id=%s AND b.is_active AND c.is_active
               ORDER BY b.assembly_sequence NULLS LAST,c.product_code""", (parent[0],))
        keys = ["productCode", "sku", "nameFa", "nameEn", "quantity", "unit", "required",
                "lossPercent", "assemblySequence", "qcRequired"]
        return [dict(zip(keys, row)) for row in cur.fetchall()]


@router.post("/master/vehicles", status_code=201)
def create_vehicle(payload: VehicleInput, request: Request,
                   principal: dict = Depends(require_permission("product.write"))):
    with _connect() as conn, conn.cursor() as cur:
        try:
            cur.execute(
                """INSERT INTO vehicle_master(vehicle_id,brand_id,brand_name,model_id,model_name,generation,
                   platform,body_type,market,engine_code,displacement,transmission_type,drive_type,model_year,notes)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (payload.vehicleId,payload.brandId,payload.brandName,payload.modelId,payload.modelName,
                 payload.generation,payload.platform,payload.bodyType,payload.market,payload.engineCode,
                 payload.displacement,payload.transmissionType,payload.driveType,payload.modelYear,payload.notes))
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(409, "Vehicle ID or model ID already exists") from exc
        vehicle_uuid = cur.fetchone()[0]
    audit(request, principal, "vehicle.create", vehicle_uuid, {"vehicle_id": payload.vehicleId})
    return {"id": vehicle_uuid, "vehicleId": payload.vehicleId, "status": "active"}


@router.post("/master/compatibility", status_code=201)
def create_compatibility(payload: CompatibilityInput, request: Request,
                         principal: dict = Depends(require_permission("product.write"))):
    if payload.yearFrom and payload.yearTo and payload.yearTo < payload.yearFrom:
        raise HTTPException(422, "yearTo must be greater than or equal to yearFrom")
    if payload.fitmentStatus not in {"CONFIRMED", "PROBABLE", "UNDER_REVIEW", "REJECTED"}:
        raise HTTPException(422, "Invalid fitment status")
    if payload.fitmentConfidence not in {"CONFIRMED", "PROBABLE", "UNDER_REVIEW", "REJECTED"}:
        raise HTTPException(422, "Invalid fitment confidence")
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM products WHERE product_code=%s AND is_active", (payload.productCode,))
        product = cur.fetchone()
        cur.execute("SELECT id FROM vehicle_master WHERE vehicle_id=%s AND is_active", (payload.vehicleId,))
        vehicle = cur.fetchone()
        if product is None or vehicle is None:
            raise HTTPException(404, "Product or vehicle not found")
        try:
            cur.execute(
                """INSERT INTO product_vehicle_compatibility
                (product_id,vehicle_id,fitment_status,position,side,engine_code,engine_volume,transmission,
                 year_from,year_to,oem_reference,fitment_confidence,notes)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (product[0],vehicle[0],payload.fitmentStatus,payload.position,payload.side,payload.engineCode,
                 payload.engineVolume,payload.transmission,payload.yearFrom,payload.yearTo,payload.oemReference,
                 payload.fitmentConfidence,payload.notes))
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(409, "Compatibility already exists") from exc
        compatibility_id = cur.fetchone()[0]
    audit(request, principal, "compatibility.create", compatibility_id,
          {"product_code": payload.productCode, "vehicle_id": payload.vehicleId,
           "fitment_status": payload.fitmentStatus})
    return {"id": compatibility_id, "status": "active"}
