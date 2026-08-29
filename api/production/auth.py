"""E.Y.T Production API identity, JWT sessions, RBAC and audit logging."""
from datetime import datetime, timedelta, timezone
import hashlib, hmac, os, secrets
from typing import Callable
from uuid import UUID

import jwt
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
ALGORITHM = "HS256"
ACCESS_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "30"))

PERMISSIONS = {"production.read", "production.execute", "qc.inspect", "qc.release", "reporting.read", "admin.users.manage", "admin.roles.manage"}

class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)
class RefreshInput(BaseModel):
    refresh_token: str = Field(min_length=40, max_length=300)
class BootstrapInput(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=12, max_length=200)
    email: str | None = Field(default=None, max_length=250)


def db_connection():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)

def secret() -> str:
    value = os.getenv("JWT_SECRET")
    if not value:
        raise RuntimeError("JWT_SECRET must be configured")
    return value

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme,n,r,p,salt_hex,digest_hex = encoded.split("$")
        if scheme != "scrypt": return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def access_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "type": "access", "iat": now, "exp": now + timedelta(minutes=ACCESS_MINUTES)}, secret(), algorithm=ALGORITHM)

def refresh_token() -> str:
    return secrets.token_urlsafe(64)

def refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def current_principal(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, secret(), algorithms=[ALGORITHM])
        if payload.get("type") != "access": raise ValueError
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token", headers={"WWW-Authenticate":"Bearer"})
    with db_connection() as conn:
        row = conn.execute("""SELECT u.id,u.username,u.email,u.is_active,COALESCE(array_agg(DISTINCT p.code) FILTER (WHERE p.code IS NOT NULL),'{}') permissions FROM eyt_users u LEFT JOIN eyt_user_roles ur ON ur.user_id=u.id LEFT JOIN eyt_role_permissions rp ON rp.role_id=ur.role_id LEFT JOIN eyt_permissions p ON p.id=rp.permission_id WHERE u.id=%s GROUP BY u.id""", (user_id,)).fetchone()
    if not row or not row[3]: raise HTTPException(401, "User is inactive or not found")
    return {"id": row[0], "username": row[1], "email": row[2], "permissions": row[4]}

def require_permission(code: str) -> Callable:
    def dependency(principal: dict = Depends(current_principal)) -> dict:
        if code not in principal["permissions"]: raise HTTPException(403, "Insufficient permission")
        return principal
    return dependency

def audit(request: Request, principal: dict, action: str, entity_id=None, metadata=None):
    with db_connection() as conn:
        conn.execute("INSERT INTO eyt_audit_logs(actor_user_id,action,entity_id,correlation_id,ip_address,metadata) VALUES(%s,%s,%s,%s,%s,%s)", (principal["id"], action, entity_id, request.headers.get("X-Correlation-ID") or secrets.token_hex(16), request.client.host if request.client else None, metadata or {}))
        conn.commit()

@router.post("/bootstrap", status_code=201)
def bootstrap(payload: BootstrapInput, request: Request):
    expected=os.getenv("BOOTSTRAP_SECRET")
    if not expected or request.headers.get("X-Bootstrap-Secret") != expected: raise HTTPException(403,"Bootstrap is disabled or unauthorized")
    with db_connection() as conn:
        if conn.execute("SELECT count(*) FROM eyt_users").fetchone()[0]: raise HTTPException(409,"Bootstrap already completed")
        role_id=conn.execute("SELECT id FROM eyt_roles WHERE name='CEO'").fetchone()[0]
        user_id=conn.execute("INSERT INTO eyt_users(username,email,password_hash) VALUES(%s,%s,%s) RETURNING id",(payload.username,payload.email,hash_password(payload.password))).fetchone()[0]
        conn.execute("INSERT INTO eyt_user_roles(user_id,role_id) VALUES(%s,%s)",(user_id,role_id)); conn.commit()
    audit(request,{"id":user_id},"auth.bootstrap",user_id); return {"id":user_id,"username":payload.username,"role":"CEO"}

@router.post("/login")
def login(payload: LoginInput, request: Request):
    with db_connection() as conn:
        row=conn.execute("SELECT id,username,password_hash,is_active FROM eyt_users WHERE username=%s",(payload.username,)).fetchone()
        if not row or not row[3] or not verify_password(payload.password,row[2]): raise HTTPException(401,"Invalid credentials",headers={"WWW-Authenticate":"Bearer"})
        token=refresh_token(); now=datetime.now(timezone.utc)
        conn.execute("UPDATE eyt_users SET last_login_at=%s WHERE id=%s",(now,row[0])); conn.execute("INSERT INTO eyt_refresh_tokens(user_id,token_hash,expires_at) VALUES(%s,%s,%s)",(row[0],refresh_hash(token),now+timedelta(days=REFRESH_DAYS))); conn.commit()
    audit(request,{"id":row[0]},"auth.login",row[0]); return {"access_token":access_token(row[0]),"token_type":"bearer","expires_in":ACCESS_MINUTES*60,"refresh_token":token}

@router.post("/refresh")
def refresh(payload: RefreshInput, request: Request):
    with db_connection() as conn:
        row=conn.execute("SELECT id,user_id FROM eyt_refresh_tokens WHERE token_hash=%s AND revoked_at IS NULL AND expires_at>now() FOR UPDATE",(refresh_hash(payload.refresh_token),)).fetchone()
        if not row: raise HTTPException(401,"Invalid or revoked refresh token")
        new=refresh_token(); new_id=conn.execute("INSERT INTO eyt_refresh_tokens(user_id,token_hash,expires_at) VALUES(%s,%s,%s) RETURNING id",(row[1],refresh_hash(new),datetime.now(timezone.utc)+timedelta(days=REFRESH_DAYS))).fetchone()[0]
        conn.execute("UPDATE eyt_refresh_tokens SET revoked_at=now(),replaced_by_id=%s WHERE id=%s",(new_id,row[0])); conn.commit()
    audit(request,{"id":row[1]},"auth.refresh",row[0]); return {"access_token":access_token(row[1]),"token_type":"bearer","expires_in":ACCESS_MINUTES*60,"refresh_token":new}

@router.post("/logout")
def logout(payload: RefreshInput, request: Request, principal: dict = Depends(current_principal)):
    with db_connection() as conn:
        conn.execute("UPDATE eyt_refresh_tokens SET revoked_at=now() WHERE token_hash=%s AND user_id=%s AND revoked_at IS NULL",(refresh_hash(payload.refresh_token),principal["id"])); conn.commit()
    audit(request,principal,"auth.logout",principal["id"]); return {"status":"logged_out"}

@router.get("/me")
def me(principal: dict = Depends(current_principal)):
    return principal
