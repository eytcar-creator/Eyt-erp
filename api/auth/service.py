"""JWT authentication, password hashing, RBAC and audit helpers."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text

from app.main import engine

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
ALGORITHM = "HS256"
ACCESS_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "30"))


def _secret() -> str:
    value = os.getenv("JWT_SECRET")
    if not value:
        raise RuntimeError("JWT_SECRET must be configured")
    return value


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$16384$8$1$%s$%s" % (salt.hex(), digest.hex())


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = encoded.split("$")
        if scheme != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "type": "access", "iat": now, "exp": now + timedelta(minutes=ACCESS_MINUTES)}, _secret(), algorithm=ALGORITHM)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def current_principal(token: str = Depends(oauth2_scheme)) -> dict:
    if engine is None:
        raise HTTPException(503, "Database is not configured")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise ValueError
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    async with engine.connect() as conn:
        row = (await conn.execute(text("""
            SELECT u.id, u.username, u.customer_id, u.is_active,
                   COALESCE(array_agg(DISTINCT p.code) FILTER (WHERE p.code IS NOT NULL), '{}') AS permissions
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN role_permissions rp ON rp.role_id = ur.role_id
            LEFT JOIN permissions p ON p.id = rp.permission_id
            WHERE u.id = :id
            GROUP BY u.id
        """), {"id": user_id})).first()
    if not row or not row.is_active:
        raise HTTPException(401, "User is inactive or not found")
    return dict(row._mapping)


def require_permission(permission: str) -> Callable:
    async def dependency(principal: dict = Depends(current_principal)) -> dict:
        if permission not in principal["permissions"]:
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return principal
    return dependency


async def audit(request: Request, principal: dict, action: str, entity_type: str | None = None, entity_id: UUID | None = None, metadata: dict | None = None):
    if engine is None:
        return
    correlation_id = request.headers.get("X-Correlation-ID") or secrets.token_hex(16)
    async with engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO audit_logs (actor_user_id, action, entity_type, entity_id, correlation_id, ip_address, metadata)
            VALUES (:actor, :action, :entity_type, :entity_id, :correlation, :ip, :metadata)
        """), {"actor": principal["id"], "action": action, "entity_type": entity_type, "entity_id": entity_id,
               "correlation": correlation_id, "ip": request.client.host if request.client else None, "metadata": metadata or {}})
