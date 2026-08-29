from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from .auth.service import audit, require_permission
from .main import engine
router=APIRouter(prefix="/api/v1",tags=["ERP Core"])
class ProductCreate(BaseModel):
 sku:str=Field(min_length=1,max_length=100); name_fa:str=Field(min_length=1,max_length=250); category_id:UUID|None=None; unit:str=Field(default="PCS",max_length=30); barcode:str|None=None; oem_code:str|None=None; brand:str|None=None; material:str|None=None; weight_kg:Decimal|None=Field(default=None,ge=0); cost_price:Decimal=Field(default=Decimal("0"),ge=0); sale_price:Decimal=Field(default=Decimal("0"),ge=0); min_stock:Decimal=Field(default=Decimal("0"),ge=0); is_sellable:bool=True; is_purchasable:bool=True; image_url:str|None=None
class StockTransaction(BaseModel):
 product_id:UUID; warehouse_id:UUID; transaction_type:str=Field(pattern="^(IN|OUT|ADJUSTMENT)$"); quantity:Decimal=Field(gt=0); transaction_no:str=Field(min_length=1,max_length=80); notes:str|None=None
async def require_engine():
 if engine is None: raise HTTPException(503,"Database is not configured")
PRODUCT_COLUMNS="p.id,p.sku,p.name_fa,p.category_id,p.unit,p.barcode,p.oem_code,p.brand,p.material,p.weight_kg,p.cost_price,p.sale_price,p.min_stock,p.is_sellable,p.is_purchasable,p.image_url,p.is_active"
@router.get("/products")
async def list_products(q:str|None=Query(default=None,max_length=100),active_only:bool=True,limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),principal:dict=Depends(require_permission("catalog.read"))):
 await require_engine(); filters=["p.is_active=true"] if active_only else []; params={"limit":limit,"offset":offset}
 if q: filters.append("(p.sku ILIKE :q OR p.name_fa ILIKE :q OR p.barcode ILIKE :q OR p.oem_code ILIKE :q)"); params["q"]=f"%{q}%"
 where=" AND ".join(filters) or "TRUE"
 async with engine.connect() as conn:
  result=await conn.execute(text(f"SELECT {PRODUCT_COLUMNS},c.name_fa category_name FROM products p LEFT JOIN product_categories c ON c.id=p.category_id WHERE {where} ORDER BY p.sku LIMIT :limit OFFSET :offset"),params); return [dict(r._mapping) for r in result]
@router.post("/products",status_code=201)
async def create_product(payload:ProductCreate,request:Request,principal:dict=Depends(require_permission("admin.users.manage"))):
 await require_engine()
 async with engine.begin() as conn:
  if (await conn.execute(text("SELECT 1 FROM products WHERE sku=:sku"),{"sku":payload.sku})).first(): raise HTTPException(409,"SKU already exists")
  result=await conn.execute(text("INSERT INTO products(sku,name_fa,category_id,unit,barcode,oem_code,brand,material,weight_kg,cost_price,sale_price,min_stock,is_sellable,is_purchasable,image_url) VALUES(:sku,:name_fa,:category_id,:unit,:barcode,:oem_code,:brand,:material,:weight_kg,:cost_price,:sale_price,:min_stock,:is_sellable,:is_purchasable,:image_url) RETURNING *"),payload.model_dump()); product=dict(result.first()._mapping)
 await audit(request,principal,"product.create","product",product["id"],{"sku":product["sku"]}); return product
@router.get("/products/{product_id}")
async def get_product(product_id:UUID,principal:dict=Depends(require_permission("catalog.read"))):
 await require_engine()
 async with engine.connect() as conn:
  row=(await conn.execute(text(f"SELECT {PRODUCT_COLUMNS},c.name_fa category_name FROM products p LEFT JOIN product_categories c ON c.id=p.category_id WHERE p.id=:id"),{"id":product_id})).first()
 if not row: raise HTTPException(404,"Product not found")
 return dict(row._mapping)
@router.get("/inventory")
async def inventory(product_id:UUID|None=None,warehouse_id:UUID|None=None,principal:dict=Depends(require_permission("inventory.read"))):
 await require_engine(); filters=[]; params={}
 if product_id: filters.append("ib.product_id=:product_id");params["product_id"]=product_id
 if warehouse_id: filters.append("ib.warehouse_id=:warehouse_id");params["warehouse_id"]=warehouse_id
 where=" AND ".join(filters) or "TRUE"
 async with engine.connect() as conn:
  result=await conn.execute(text(f"SELECT ib.product_id,p.sku,p.name_fa,ib.warehouse_id,w.code warehouse_code,w.name_fa warehouse_name,ib.on_hand_qty,ib.reserved_qty,(ib.on_hand_qty-ib.reserved_qty) available_qty,ib.reorder_point,ib.updated_at FROM inventory_balances ib JOIN products p ON p.id=ib.product_id JOIN warehouses w ON w.id=ib.warehouse_id WHERE {where} ORDER BY p.sku,w.code"),params);return [dict(r._mapping) for r in result]
@router.post("/inventory/transactions",status_code=201)
async def post_stock_transaction(payload:StockTransaction,request:Request,principal:dict=Depends(require_permission("inventory.adjust"))):
 await require_engine(); delta=payload.quantity*(1 if payload.transaction_type in {"IN","ADJUSTMENT"} else -1)
 async with engine.begin() as conn:
  if not (await conn.execute(text("SELECT 1 FROM products WHERE id=:id AND is_active=true"),{"id":payload.product_id})).first(): raise HTTPException(404,"Product not found")
  if not (await conn.execute(text("SELECT 1 FROM warehouses WHERE id=:id AND is_active=true"),{"id":payload.warehouse_id})).first(): raise HTTPException(404,"Warehouse not found")
  if (await conn.execute(text("SELECT 1 FROM inventory_transactions WHERE transaction_no=:no"),{"no":payload.transaction_no})).first(): raise HTTPException(409,"Transaction number already exists")
  row=(await conn.execute(text("SELECT on_hand_qty,reserved_qty FROM inventory_balances WHERE product_id=:product_id AND warehouse_id=:warehouse_id FOR UPDATE"),{"product_id":payload.product_id,"warehouse_id":payload.warehouse_id})).first(); on_hand,reserved=(Decimal(row.on_hand_qty),Decimal(row.reserved_qty)) if row else (Decimal("0"),Decimal("0")); new=on_hand+delta
  if new<reserved or new<0: raise HTTPException(409,"Insufficient available stock")
  if row: await conn.execute(text("UPDATE inventory_balances SET on_hand_qty=:qty,updated_at=now() WHERE product_id=:product_id AND warehouse_id=:warehouse_id"),{"qty":new,"product_id":payload.product_id,"warehouse_id":payload.warehouse_id})
  else: await conn.execute(text("INSERT INTO inventory_balances(product_id,warehouse_id,on_hand_qty) VALUES(:product_id,:warehouse_id,:qty)"),{"product_id":payload.product_id,"warehouse_id":payload.warehouse_id,"qty":new})
  result=await conn.execute(text("INSERT INTO inventory_transactions(transaction_no,product_id,warehouse_id,transaction_type,quantity,notes) VALUES(:no,:product_id,:warehouse_id,:type,:quantity,:notes) RETURNING *"),{"no":payload.transaction_no,"product_id":payload.product_id,"warehouse_id":payload.warehouse_id,"type":payload.transaction_type,"quantity":payload.quantity,"notes":payload.notes}); transaction=dict(result.first()._mapping)
 await audit(request,principal,"inventory.adjust","inventory_transaction",transaction["id"],{"transaction_no":transaction["transaction_no"]});return transaction
@router.get("/dashboard/summary")
async def dashboard_summary(principal:dict=Depends(require_permission("reporting.read"))):
 await require_engine()
 async with engine.connect() as conn:
  row=(await conn.execute(text("SELECT (SELECT count(*) FROM products WHERE is_active=true) active_products,(SELECT count(*) FROM customers WHERE is_active=true) active_customers,(SELECT count(*) FROM suppliers WHERE is_active=true) active_suppliers,(SELECT coalesce(sum(on_hand_qty),0) FROM inventory_balances) total_units_on_hand,(SELECT count(*) FROM sales_orders WHERE status IN ('DRAFT','CONFIRMED','RESERVED','PARTIAL')) open_sales_orders,(SELECT count(*) FROM production_orders WHERE status IN ('PLANNED','RELEASED','IN_PROGRESS')) active_production_orders"))).first();return dict(row._mapping)
