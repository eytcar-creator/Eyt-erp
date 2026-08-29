from contextlib import contextmanager
import os, hashlib, secrets
from datetime import datetime, timedelta, timezone
from typing import Any
import psycopg
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

DATABASE_URL=os.getenv("DATABASE_URL","")
APP_ENV=os.getenv("APP_ENV","development")
TOKEN_TTL_HOURS=int(os.getenv("TOKEN_TTL_HOURS","12"))
bearer=HTTPBearer(auto_error=False)

app=FastAPI(title="E.Y.T ERP API",version="1.2.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS","*").split(",")],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])

RESOURCES={
"customers":{"table":"customers","fields":["name","phone","email","address"]},
"suppliers":{"table":"suppliers","fields":["name","phone","email","address"]},
"products":{"table":"products","fields":["sku","name","name_fa","category_id","unit"]},
"warehouses":{"table":"warehouses","fields":["code","name","name_fa","address","is_active"]},
"purchase-requests":{"table":"purchase_requests","fields":["request_no","requested_by","warehouse_id","status","required_date","notes"]},
"purchase-orders":{"table":"purchase_orders","fields":["po_no","supplier_id","warehouse_id","request_id","order_date","expected_date","status","currency","notes"]},
"production-orders":{"table":"production_orders","fields":["production_no","product_id","bom_id","warehouse_id","planned_quantity","completed_quantity","planned_start","planned_end","status","notes"]},
"mrp-recommendations":{"table":"mrp_recommendations","fields":["mrp_run_id","product_id","warehouse_id","recommendation_type","required_quantity","available_quantity","net_requirement","recommended_date","status"]},
"shortage-alerts":{"table":"material_shortage_alerts","fields":["product_id","warehouse_id","production_order_id","mrp_run_id","required_quantity","available_quantity","shortage_quantity","severity","status","notes"]},
"receivables":{"table":"receivables","fields":["receivable_no","customer_id","invoice_id","issue_date","due_date","original_amount","paid_amount","status","notes"]},
"payables":{"table":"payables","fields":["payable_no","supplier_id","purchase_order_id","issue_date","due_date","original_amount","paid_amount","status","notes"]},
"cash-transactions":{"table":"cash_transactions","fields":["transaction_no","financial_account_id","transaction_type","amount","transaction_date","reference_type","reference_id","description"]},
}

class RecordIn(BaseModel): data:dict[str,Any]=Field(default_factory=dict)
class LoginIn(BaseModel): username:str; password:str
class UserCreate(BaseModel): username:str; password:str; full_name:str|None=None; is_admin:bool=False

@contextmanager
def db():
    if not DATABASE_URL: raise HTTPException(status_code=503,detail="DATABASE_URL is not configured")
    try:
        with psycopg.connect(DATABASE_URL,row_factory=dict_row) as conn: yield conn
    except HTTPException: raise
    except Exception as exc: raise HTTPException(status_code=503,detail=f"Database unavailable: {exc}") from exc

def hash_password(password,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+"$"+hashlib.pbkdf2_hmac("sha256",password.encode(),salt.encode(),200000).hex()
def verify_password(password,stored):
    salt,_=stored.split("$",1)
    return secrets.compare_digest(hash_password(password,salt),stored)

def init_auth(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS app_users(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),username varchar(80) UNIQUE NOT NULL,password_hash text NOT NULL,full_name varchar(200),is_admin boolean NOT NULL DEFAULT false,is_active boolean NOT NULL DEFAULT true,created_at timestamptz NOT NULL DEFAULT now())")
    conn.execute("CREATE TABLE IF NOT EXISTS app_sessions(token_hash varchar(64) PRIMARY KEY,user_id uuid REFERENCES app_users(id) ON DELETE CASCADE,expires_at timestamptz NOT NULL,created_at timestamptz NOT NULL DEFAULT now())")
    conn.commit()

def current_user(creds:HTTPAuthorizationCredentials|None=Depends(bearer)):
    if not creds: raise HTTPException(status_code=401,detail="Authentication required")
    h=hashlib.sha256(creds.credentials.encode()).hexdigest()
    with db() as c:
        init_auth(c)
        row=c.execute("SELECT u.* FROM app_sessions s JOIN app_users u ON u.id=s.user_id WHERE s.token_hash=%s AND s.expires_at>now() AND u.is_active=true",(h,)).fetchone()
    if not row: raise HTTPException(status_code=401,detail="Invalid or expired session")
    return row

def require_admin(user=Depends(current_user)):
    if not user["is_admin"]: raise HTTPException(status_code=403,detail="Administrator permission required")
    return user

def resource_or_404(name):
    r=RESOURCES.get(name)
    if not r: raise HTTPException(status_code=404,detail="Unknown ERP resource")
    return r
def clean_data(resource,data):
    p={k:v for k,v in data.items() if k in resource["fields"]}
    if not p: raise HTTPException(status_code=422,detail="No allowed fields supplied")
    return p

@app.get("/api/v1/health")
def health():
    if not DATABASE_URL:return {"status":"ok","database":"not_configured","environment":APP_ENV}
    with db() as c:c.execute("SELECT 1")
    return {"status":"ok","database":"ok","environment":APP_ENV}

@app.post("/api/v1/auth/bootstrap")
def bootstrap(body:UserCreate):
    with db() as c:
        init_auth(c)
        if c.execute("SELECT count(*) n FROM app_users").fetchone()["n"]: raise HTTPException(status_code=409,detail="Bootstrap already completed")
        row=c.execute("INSERT INTO app_users(username,password_hash,full_name,is_admin) VALUES(%s,%s,%s,true) RETURNING id,username,full_name,is_admin",(body.username,hash_password(body.password),body.full_name)).fetchone();c.commit()
    return row

@app.post("/api/v1/auth/login")
def login(body:LoginIn):
    with db() as c:
        init_auth(c);u=c.execute("SELECT * FROM app_users WHERE username=%s AND is_active=true",(body.username,)).fetchone()
        if not u or not verify_password(body.password,u["password_hash"]): raise HTTPException(status_code=401,detail="Invalid credentials")
        token=secrets.token_urlsafe(32); exp=datetime.now(timezone.utc)+timedelta(hours=TOKEN_TTL_HOURS)
        c.execute("INSERT INTO app_sessions(token_hash,user_id,expires_at) VALUES(%s,%s,%s)",(hashlib.sha256(token.encode()).hexdigest(),u["id"],exp));c.commit()
    return {"access_token":token,"token_type":"bearer","expires_at":exp}

@app.get("/api/v1/auth/me")
def me(user=Depends(current_user)): return {"id":str(user["id"]),"username":user["username"],"full_name":user["full_name"],"is_admin":user["is_admin"]}

@app.post("/api/v1/auth/users")
def create_user(body:UserCreate,_=Depends(require_admin)):
    with db() as c:
        init_auth(c);row=c.execute("INSERT INTO app_users(username,password_hash,full_name,is_admin) VALUES(%s,%s,%s,%s) RETURNING id,username,full_name,is_admin",(body.username,hash_password(body.password),body.full_name,body.is_admin)).fetchone();c.commit()
    return row

@app.get("/api/v1/resources")
def resources(_=Depends(current_user)): return {"resources":[{"name":n,"fields":v["fields"]} for n,v in RESOURCES.items()]}

@app.get("/api/v1/{resource}")
def list_records(resource:str,limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),_=Depends(current_user)):
    s=resource_or_404(resource)
    with db() as c:rows=c.execute(f"SELECT * FROM {s['table']} ORDER BY id DESC LIMIT %s OFFSET %s",(limit,offset)).fetchall()
    return {"items":rows,"limit":limit,"offset":offset}

@app.get("/api/v1/{resource}/{record_id}")
def get_record(resource:str,record_id:str,_=Depends(current_user)):
    s=resource_or_404(resource)
    with db() as c:row=c.execute(f"SELECT * FROM {s['table']} WHERE id=%s",(record_id,)).fetchone()
    if not row: raise HTTPException(status_code=404,detail="Record not found")
    return row

@app.post("/api/v1/{resource}",status_code=201)
def create_record(resource:str,body:RecordIn,_=Depends(current_user)):
    s=resource_or_404(resource);p=clean_data(s,body.data);cols=list(p)
    with db() as c:row=c.execute(f"INSERT INTO {s['table']} ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))}) RETURNING *",[p[k] for k in cols]).fetchone();c.commit()
    return row

@app.patch("/api/v1/{resource}/{record_id}")
def update_record(resource:str,record_id:str,body:RecordIn,_=Depends(current_user)):
    s=resource_or_404(resource);p=clean_data(s,body.data)
    with db() as c:row=c.execute(f"UPDATE {s['table']} SET "+", ".join(f"{k}=%s" for k in p)+" WHERE id=%s RETURNING *",list(p.values())+[record_id]).fetchone();c.commit()
    if not row: raise HTTPException(status_code=404,detail="Record not found")
    return row

@app.get("/api/v1/dashboard/summary")
def dashboard_summary(_=Depends(current_user)):
    checks={"open_receivables":"SELECT COALESCE(SUM(original_amount-paid_amount),0) value FROM receivables WHERE status IN ('OPEN','PARTIAL','OVERDUE')","open_payables":"SELECT COALESCE(SUM(original_amount-paid_amount),0) value FROM payables WHERE status IN ('OPEN','PARTIAL','OVERDUE')","open_shortages":"SELECT COUNT(*) value FROM material_shortage_alerts WHERE status IN ('OPEN','ACKNOWLEDGED')","active_production":"SELECT COUNT(*) value FROM production_orders WHERE status IN ('PLANNED','RELEASED','IN_PROGRESS','PAUSED')","queued_automation":"SELECT COUNT(*) value FROM automation_jobs WHERE status IN ('QUEUED','RUNNING')"}
    with db() as c:return {k:c.execute(v).fetchone()["value"] for k,v in checks.items()}
