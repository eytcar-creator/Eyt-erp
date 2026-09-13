from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/customer-market", tags=["Customer & Market"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=80)
    city: Optional[str] = Field(default=None, max_length=100)
    customerType: str = Field(default="CONSUMER", max_length=30)
    source: Optional[str] = Field(default=None, max_length=80)
    marketingSource: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = None


class VehicleLinkIn(BaseModel):
    vehicleId: str
    plateNo: Optional[str] = None
    modelYear: Optional[str] = None
    mileageKm: Optional[int] = Field(default=None, ge=0)
    vin: Optional[str] = None
    isPrimary: bool = False
    notes: Optional[str] = None


class MechanicIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    specialty: Optional[str] = None


class StoreIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    address: Optional[str] = None


class InstallationIn(BaseModel):
    customerId: str
    customerVehicleId: Optional[str] = None
    productId: str
    orderId: Optional[str] = None
    mechanicId: Optional[str] = None
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    mileageKm: Optional[int] = Field(default=None, ge=0)
    warrantyUntil: Optional[date] = None
    notes: Optional[str] = None


class PurchaseIn(BaseModel):
    customerId: str
    customerVehicleId: Optional[str] = None
    orderId: Optional[str] = None
    productId: str
    quantity: Decimal = Field(gt=0)
    unitPrice: Decimal = Field(default=Decimal("0"), ge=0)
    source: str = Field(default="DIRECT", max_length=50)
    nextExpectedPurchase: Optional[date] = None
    notes: Optional[str] = None


def _customer_code(cur) -> str:
    cur.execute("SELECT COALESCE(MAX(CAST(NULLIF(regexp_replace(customer_code,'\\D','','g'),'') AS BIGINT)),0)+1 FROM customers")
    n = cur.fetchone()[0]
    return f"C-{int(n):06d}"


def _mechanic_code(cur) -> str:
    cur.execute("SELECT COUNT(*)+1 FROM mechanics")
    return f"M-{int(cur.fetchone()[0]):06d}"


def _store_code(cur) -> str:
    cur.execute("SELECT COUNT(*)+1 FROM parts_stores")
    return f"S-{int(cur.fetchone()[0]):06d}"


@router.get("/dashboard")
def dashboard():
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM customers WHERE is_active")
        customers = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM customer_vehicles")
        vehicles = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM mechanics WHERE status='ACTIVE'")
        mechanics = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM parts_stores WHERE status='ACTIVE'")
        stores = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sales_orders WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'")
        orders30 = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT customer_id) FROM sales_orders WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'")
        buyers30 = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM repeat_purchase_reminders WHERE status='OPEN' AND due_date <= CURRENT_DATE + 30")
        reminders = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(subtotal),0) FROM sales_orders WHERE created_at >= CURRENT_DATE - INTERVAL '30 days' AND status <> 'CANCELLED'")
        sales30 = cur.fetchone()[0]
    return {"customers": customers, "vehicles": vehicles, "mechanics": mechanics, "stores": stores,
            "orders30": orders30, "buyers30": buyers30, "repeatReminders30": reminders,
            "sales30": Decimal(str(sales30))}


@router.get("/customers")
def customers(search: str = "", city: str = "", limit: int = Query(100, ge=1, le=500)):
    with _connect() as conn, conn.cursor() as cur:
        like = f"%{search.strip()}%"
        cur.execute("""SELECT c.id,c.customer_code,c.name,c.phone,c.city,c.customer_type,c.source,c.marketing_source,
                              c.created_at, COUNT(DISTINCT cv.id) vehicle_count,
                              COUNT(DISTINCT ph.id) purchase_count,
                              COALESCE(SUM(ph.quantity*ph.unit_price),0) lifetime_value
                       FROM customers c
                       LEFT JOIN customer_vehicles cv ON cv.customer_id=c.id
                       LEFT JOIN purchase_history ph ON ph.customer_id=c.id
                       WHERE c.is_active AND (%s='' OR c.name ILIKE %s OR COALESCE(c.phone,'') ILIKE %s OR c.customer_code ILIKE %s)
                         AND (%s='' OR COALESCE(c.city,'') ILIKE %s)
                       GROUP BY c.id ORDER BY c.created_at DESC LIMIT %s""",
                    (search, like, like, like, city, f"%{city}%", limit))
        rows = cur.fetchall()
    return [{"id": str(r[0]), "code": r[1], "name": r[2], "phone": r[3], "city": r[4],
             "type": r[5], "source": r[6], "marketingSource": r[7], "createdAt": r[8],
             "vehicleCount": r[9], "purchaseCount": r[10], "lifetimeValue": Decimal(str(r[11]))} for r in rows]


@router.post("/customers")
def create_customer(payload: CustomerIn):
    with _connect() as conn, conn.cursor() as cur:
        code = _customer_code(cur)
        cur.execute("""INSERT INTO customers(customer_code,name,phone,city,customer_type,source,marketing_source,notes)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id,customer_code""",
                    (code,payload.name,payload.phone,payload.city,payload.customerType,payload.source,payload.marketingSource,payload.notes))
        row = cur.fetchone()
        conn.commit()
    return {"id": str(row[0]), "code": row[1], "status": "created"}


@router.get("/customers/{customer_id}")
def customer_detail(customer_id: str):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id,customer_code,name,phone,email,city,customer_type,source,marketing_source,notes,created_at FROM customers WHERE id=%s", (customer_id,))
        c = cur.fetchone()
        if not c: raise HTTPException(404, "Customer not found")
        cur.execute("""SELECT cv.id,vm.vehicle_id,vm.brand_name,vm.model_name,cv.plate_no,cv.model_year,cv.mileage_km,cv.vin,cv.is_primary
                       FROM customer_vehicles cv JOIN vehicle_master vm ON vm.id=cv.vehicle_id WHERE cv.customer_id=%s ORDER BY cv.is_primary DESC,cv.created_at DESC""", (customer_id,))
        vehicles = cur.fetchall()
        cur.execute("""SELECT ph.id,ph.product_id,p.product_code,p.name_fa,ph.quantity,ph.unit_price,ph.purchased_at,ph.source,ph.next_expected_purchase
                       FROM purchase_history ph JOIN products p ON p.id=ph.product_id WHERE ph.customer_id=%s ORDER BY ph.purchased_at DESC LIMIT 100""", (customer_id,))
        purchases = cur.fetchall()
        cur.execute("""SELECT i.id,p.product_code,p.name_fa,i.installed_at,i.quantity,m.name mechanic_name,i.mileage_km,i.warranty_until
                       FROM installations i JOIN products p ON p.id=i.product_id LEFT JOIN mechanics m ON m.id=i.mechanic_id
                       WHERE i.customer_id=%s ORDER BY i.installed_at DESC LIMIT 100""", (customer_id,))
        installs = cur.fetchall()
    return {"customer":{"id":str(c[0]),"code":c[1],"name":c[2],"phone":c[3],"email":c[4],"city":c[5],"type":c[6],"source":c[7],"marketingSource":c[8],"notes":c[9],"createdAt":c[10]},
            "vehicles":[{"id":str(r[0]),"vehicleId":str(r[1]),"brand":r[2],"model":r[3],"plate":r[4],"year":r[5],"mileageKm":r[6],"vin":r[7],"primary":r[8]} for r in vehicles],
            "purchases":[{"id":str(r[0]),"productId":str(r[1]),"productCode":r[2],"productName":r[3],"quantity":r[4],"unitPrice":r[5],"purchasedAt":r[6],"source":r[7],"nextExpectedPurchase":r[8]} for r in purchases],
            "installations":[{"id":str(r[0]),"productCode":r[1],"productName":r[2],"installedAt":r[3],"quantity":r[4],"mechanic":r[5],"mileageKm":r[6],"warrantyUntil":r[7]} for r in installs]}


@router.post("/customers/{customer_id}/vehicles")
def link_vehicle(customer_id: str, payload: VehicleLinkIn):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM customers WHERE id=%s", (customer_id,))
        if not cur.fetchone(): raise HTTPException(404, "Customer not found")
        if payload.isPrimary:
            cur.execute("UPDATE customer_vehicles SET is_primary=FALSE WHERE customer_id=%s", (customer_id,))
        cur.execute("""INSERT INTO customer_vehicles(customer_id,vehicle_id,plate_no,model_year,mileage_km,vin,is_primary,notes)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (customer_id,payload.vehicleId,payload.plateNo,payload.modelYear,payload.mileageKm,payload.vin,payload.isPrimary,payload.notes))
        rid=cur.fetchone()[0]; conn.commit()
    return {"id":str(rid),"status":"linked"}


@router.get("/vehicles")
def vehicles(search: str = "", limit: int = Query(200, ge=1, le=500)):
    with _connect() as conn, conn.cursor() as cur:
        like=f"%{search}%"
        cur.execute("""SELECT id,vehicle_id,brand_name,model_name,model_year,market FROM vehicle_master
                       WHERE is_active AND (%s='' OR brand_name ILIKE %s OR model_name ILIKE %s OR vehicle_id ILIKE %s)
                       ORDER BY brand_name,model_name LIMIT %s""", (search,like,like,like,limit))
        rows=cur.fetchall()
    return [{"id":str(r[0]),"vehicleId":r[1],"brand":r[2],"model":r[3],"year":r[4],"market":r[5]} for r in rows]


@router.post("/mechanics")
def create_mechanic(payload: MechanicIn):
    with _connect() as conn, conn.cursor() as cur:
        code=_mechanic_code(cur)
        cur.execute("INSERT INTO mechanics(mechanic_code,name,phone,city,area,specialty) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id,mechanic_code",(code,payload.name,payload.phone,payload.city,payload.area,payload.specialty))
        r=cur.fetchone(); conn.commit()
    return {"id":str(r[0]),"code":r[1],"status":"created"}


@router.get("/mechanics")
def list_mechanics(search: str = "", limit: int = Query(200, ge=1, le=500)):
    with _connect() as conn, conn.cursor() as cur:
        like=f"%{search}%"
        cur.execute("""SELECT m.id,m.mechanic_code,m.name,m.phone,m.city,m.area,m.specialty,
                              COUNT(DISTINCT i.id) installs,COUNT(DISTINCT r.customer_id) customers
                       FROM mechanics m LEFT JOIN installations i ON i.mechanic_id=m.id LEFT JOIN referrals r ON r.mechanic_id=m.id
                       WHERE m.status='ACTIVE' AND (%s='' OR m.name ILIKE %s OR COALESCE(m.phone,'') ILIKE %s OR COALESCE(m.city,'') ILIKE %s)
                       GROUP BY m.id ORDER BY installs DESC,m.name LIMIT %s""",(search,like,like,like,limit))
        rows=cur.fetchall()
    return [{"id":str(r[0]),"code":r[1],"name":r[2],"phone":r[3],"city":r[4],"area":r[5],"specialty":r[6],"installations":r[7],"customers":r[8]} for r in rows]


@router.post("/stores")
def create_store(payload: StoreIn):
    with _connect() as conn, conn.cursor() as cur:
        code=_store_code(cur)
        cur.execute("INSERT INTO parts_stores(store_code,name,phone,city,area,address) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id,store_code",(code,payload.name,payload.phone,payload.city,payload.area,payload.address))
        r=cur.fetchone(); conn.commit()
    return {"id":str(r[0]),"code":r[1],"status":"created"}


@router.get("/stores")
def list_stores(search: str = "", limit: int = Query(200, ge=1, le=500)):
    with _connect() as conn, conn.cursor() as cur:
        like=f"%{search}%"
        cur.execute("SELECT id,store_code,name,phone,city,area,address FROM parts_stores WHERE status='ACTIVE' AND (%s='' OR name ILIKE %s OR COALESCE(phone,'') ILIKE %s OR COALESCE(city,'') ILIKE %s) ORDER BY name LIMIT %s",(search,like,like,like,limit))
        rows=cur.fetchall()
    return [{"id":str(r[0]),"code":r[1],"name":r[2],"phone":r[3],"city":r[4],"area":r[5],"address":r[6]} for r in rows]


@router.post("/installations")
def create_installation(payload: InstallationIn):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO installations(customer_id,customer_vehicle_id,product_id,order_id,mechanic_id,quantity,mileage_km,warranty_until,notes)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",(payload.customerId,payload.customerVehicleId,payload.productId,payload.orderId,payload.mechanicId,payload.quantity,payload.mileageKm,payload.warrantyUntil,payload.notes))
        rid=cur.fetchone()[0]; conn.commit()
    return {"id":str(rid),"status":"recorded"}


@router.post("/purchases")
def record_purchase(payload: PurchaseIn):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO purchase_history(customer_id,customer_vehicle_id,order_id,product_id,quantity,unit_price,source,next_expected_purchase,notes)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",(payload.customerId,payload.customerVehicleId,payload.orderId,payload.productId,payload.quantity,payload.unitPrice,payload.source,payload.nextExpectedPurchase,payload.notes))
        rid=cur.fetchone()[0]
        if payload.nextExpectedPurchase:
            cur.execute("""INSERT INTO repeat_purchase_reminders(customer_id,customer_vehicle_id,product_id,last_purchase_id,due_date)
                           VALUES(%s,%s,%s,%s,%s)""",(payload.customerId,payload.customerVehicleId,payload.productId,rid,payload.nextExpectedPurchase))
        conn.commit()
    return {"id":str(rid),"status":"recorded"}


@router.get("/repeat-purchases")
def repeat_purchases(status: str = "OPEN", limit: int = Query(100, ge=1, le=500)):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT r.id,r.due_date,c.customer_code,c.name,c.phone,vm.brand_name,vm.model_name,p.product_code,p.name_fa
                       FROM repeat_purchase_reminders r JOIN customers c ON c.id=r.customer_id
                       LEFT JOIN customer_vehicles cv ON cv.id=r.customer_vehicle_id LEFT JOIN vehicle_master vm ON vm.id=cv.vehicle_id
                       JOIN products p ON p.id=r.product_id WHERE r.status=%s ORDER BY r.due_date LIMIT %s""",(status,limit))
        rows=cur.fetchall()
    return [{"id":str(r[0]),"dueDate":r[1],"customerCode":r[2],"customerName":r[3],"phone":r[4],"vehicle":f"{r[5] or ''} {r[6] or ''}".strip(),"productCode":r[7],"productName":r[8]} for r in rows]
