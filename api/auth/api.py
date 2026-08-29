from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from app.main import engine
from .service import ACCESS_MINUTES, REFRESH_DAYS, audit, create_access_token, create_refresh_token, current_principal, hash_password, refresh_hash, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)
class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=40, max_length=300)
class BootstrapRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    email: str | None = Field(default=None, max_length=250)
    password: str = Field(min_length=12, max_length=200)

@router.post("/login")
async def login(payload: LoginRequest, request: Request):
    if engine is None: raise HTTPException(503, "Database is not configured")
    async with engine.begin() as conn:
        row=(await conn.execute(text("SELECT id, username, password_hash, is_active, customer_id FROM users WHERE username=:username"),{"username":payload.username})).first()
        if not row or not row.is_active or not verify_password(payload.password,row.password_hash): raise HTTPException(401,"Invalid credentials",headers={"WWW-Authenticate":"Bearer"})
        refresh=create_refresh_token(); now=datetime.now(timezone.utc)
        await conn.execute(text("UPDATE users SET last_login_at=:now WHERE id=:id"),{"now":now,"id":row.id})
        await conn.execute(text("INSERT INTO refresh_tokens(user_id,token_hash,expires_at) VALUES(:user,:hash,:exp)"),{"user":row.id,"hash":refresh_hash(refresh),"exp":now+timedelta(days=REFRESH_DAYS)})
    await audit(request,{"id":row.id},"auth.login","user",row.id)
    return {"access_token":create_access_token(row.id),"token_type":"bearer","expires_in":ACCESS_MINUTES*60,"refresh_token":refresh}

@router.post("/refresh")
async def refresh(payload: RefreshRequest, request: Request):
    if engine is None: raise HTTPException(503,"Database is not configured")
    async with engine.begin() as conn:
        row=(await conn.execute(text("SELECT rt.id,rt.user_id,u.is_active FROM refresh_tokens rt JOIN users u ON u.id=rt.user_id WHERE rt.token_hash=:hash AND rt.revoked_at IS NULL AND rt.expires_at>now() FOR UPDATE"),{"hash":refresh_hash(payload.refresh_token)})).first()
        if not row or not row.is_active: raise HTTPException(401,"Invalid or revoked refresh token")
        new_refresh=create_refresh_token(); new_id=(await conn.execute(text("INSERT INTO refresh_tokens(user_id,token_hash,expires_at) VALUES(:user,:hash,:exp) RETURNING id"),{"user":row.user_id,"hash":refresh_hash(new_refresh),"exp":datetime.now(timezone.utc)+timedelta(days=REFRESH_DAYS)})).scalar_one()
        await conn.execute(text("UPDATE refresh_tokens SET revoked_at=now(),replaced_by_id=:new WHERE id=:old"),{"new":new_id,"old":row.id})
    await audit(request,{"id":row.user_id},"auth.refresh","refresh_token",row.id)
    return {"access_token":create_access_token(row.user_id),"token_type":"bearer","expires_in":ACCESS_MINUTES*60,"refresh_token":new_refresh}

@router.post("/logout")
async def logout(payload: RefreshRequest, request: Request, principal: dict = Depends(current_principal)):
    if engine is None: raise HTTPException(503,"Database is not configured")
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE refresh_tokens SET revoked_at=now() WHERE token_hash=:hash AND user_id=:user AND revoked_at IS NULL"),{"hash":refresh_hash(payload.refresh_token),"user":principal["id"]})
    await audit(request,principal,"auth.logout","user",principal["id"]); return {"status":"logged_out"}

@router.get("/me")
async def me(principal: dict = Depends(current_principal)):
    return {"id":principal["id"],"username":principal["username"],"customer_id":principal["customer_id"],"permissions":principal["permissions"]}

@router.post("/bootstrap",status_code=201)
async def bootstrap(payload: BootstrapRequest, request: Request):
    import os
    expected=os.getenv("BOOTSTRAP_SECRET")
    if not expected or request.headers.get("X-Bootstrap-Secret")!=expected: raise HTTPException(403,"Bootstrap is disabled or unauthorized")
    if engine is None: raise HTTPException(503,"Database is not configured")
    async with engine.begin() as conn:
        if (await conn.execute(text("SELECT count(*) FROM users"))).scalar_one(): raise HTTPException(409,"Bootstrap already completed")
        user_id=(await conn.execute(text("INSERT INTO users(username,email,password_hash) VALUES(:username,:email,:hash) RETURNING id"),{"username":payload.username,"email":payload.email,"hash":hash_password(payload.password)})).scalar_one()
        role_id=(await conn.execute(text("SELECT id FROM roles WHERE name='CEO'"))).scalar_one()
        await conn.execute(text("INSERT INTO user_roles(user_id,role_id) VALUES(:user,:role)"),{"user":user_id,"role":role_id})
    await audit(request,{"id":user_id},"auth.bootstrap","user",user_id); return {"id":user_id,"username":payload.username,"role":"CEO"}
