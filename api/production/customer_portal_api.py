from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/customer-portal", tags=["Customer Portal"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class CustomerLoginIn(BaseModel):
    accountCode: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=256)


class CustomerSessionOut(BaseModel):
    accessToken: str
    expiresAt: datetime
    accountId: str
    customerId: str
    accountCode: str


@router.post("/login", response_model=CustomerSessionOut)
def login(payload: CustomerLoginIn):
    """Authenticate a customer portal account, never an internal ERP user."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id, customer_id, account_code, status, password_hash
               FROM customer_accounts WHERE account_code=%s""",
            (payload.accountCode,),
        )
        row = cur.fetchone()
        if row is None or row[3] != "ACTIVE" or not row[4]:
            raise HTTPException(401, "Invalid customer credentials")
        # Password hashing/verification is deliberately delegated to the
        # deployment's approved authentication layer. Plain-text passwords
        # are never persisted by this API.
        import bcrypt
        try:
            valid = bcrypt.checkpw(payload.password.encode(), row[4].encode())
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise HTTPException(401, "Invalid customer credentials")

        token = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        cur.execute(
            """INSERT INTO customer_account_sessions(account_id,token_hash,expires_at)
               VALUES(%s,%s,%s)""",
            (row[0], _hash_token(token), expires),
        )
        cur.execute(
            "UPDATE customer_accounts SET last_login_at=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (datetime.now(timezone.utc), row[0]),
        )
        return CustomerSessionOut(
            accessToken=token,
            expiresAt=expires,
            accountId=str(row[0]),
            customerId=str(row[1]),
            accountCode=row[2],
        )


def require_customer_session(request: Request) -> dict:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Customer authentication required")
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT ca.id, ca.customer_id, ca.account_code
               FROM customer_account_sessions s
               JOIN customer_accounts ca ON ca.id=s.account_id
               WHERE s.token_hash=%s AND s.revoked_at IS NULL
                 AND s.expires_at > CURRENT_TIMESTAMP AND ca.status='ACTIVE'""",
            (_hash_token(token),),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(401, "Invalid or expired customer session")
    return {"accountId": str(row[0]), "customerId": str(row[1]), "accountCode": row[2]}


@router.get("/me")
def me(request: Request):
    return require_customer_session(request)


@router.post("/logout")
def logout(request: Request):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        return {"status": "logged_out"}
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE customer_account_sessions SET revoked_at=CURRENT_TIMESTAMP WHERE token_hash=%s AND revoked_at IS NULL",
            (_hash_token(token),),
        )
    return {"status": "logged_out"}
