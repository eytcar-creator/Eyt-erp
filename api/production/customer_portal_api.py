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
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT id, customer_id, account_code, status, password_hash
                       FROM customer_accounts WHERE account_code=%s""", (payload.accountCode.strip(),))
        row = cur.fetchone()
        if row is None or row[3] != "ACTIVE" or not row[4]:
            raise HTTPException(401, "Invalid customer credentials")
        import bcrypt
        try:
            valid = bcrypt.checkpw(payload.password.encode(), row[4].encode())
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise HTTPException(401, "Invalid customer credentials")
        token = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        cur.execute("""INSERT INTO customer_account_sessions(account_id,token_hash,expires_at)
                       VALUES(%s,%s,%s)""", (row[0], _hash_token(token), expires))
        cur.execute("UPDATE customer_accounts SET last_login_at=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (datetime.now(timezone.utc), row[0]))
        conn.commit()
        return CustomerSessionOut(accessToken=token, expiresAt=expires, accountId=str(row[0]),
                                  customerId=str(row[1]), accountCode=row[2])


def require_customer_session(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Customer authentication required")
    token = auth[7:].strip()
    if not token:
        raise HTTPException(401, "Customer authentication required")
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT ca.id, ca.customer_id, ca.account_code
                       FROM customer_account_sessions s
                       JOIN customer_accounts ca ON ca.id=s.account_id
                       WHERE s.token_hash=%s AND s.revoked_at IS NULL
                         AND s.expires_at > CURRENT_TIMESTAMP AND ca.status='ACTIVE'""",
                    (_hash_token(token),))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(401, "Invalid or expired customer session")
    return {"accountId": str(row[0]), "customerId": str(row[1]), "accountCode": row[2]}


@router.get("/me")
def me(request: Request):
    session = require_customer_session(request)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT c.name, c.phone, c.email FROM customers c WHERE c.id=%s", (session["customerId"],))
        row = cur.fetchone()
    return {**session, "customerName": row[0] if row else None, "phone": row[1] if row else None,
            "email": row[2] if row else None}


@router.post("/logout")
def logout(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return {"status": "logged_out"}
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""UPDATE customer_account_sessions SET revoked_at=CURRENT_TIMESTAMP
                       WHERE token_hash=%s AND revoked_at IS NULL""", (_hash_token(auth[7:].strip()),))
        conn.commit()
    return {"status": "logged_out"}


@router.get("/orders")
def customer_orders(request: Request, limit: int = 50):
    session = require_customer_session(request)
    limit = max(1, min(limit, 100))
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT order_no, status, channel, warehouse_code, payment_type,
                              created_at, confirmed_at
                       FROM sales_orders
                       WHERE customer_id=%s
                       ORDER BY created_at DESC LIMIT %s""", (session["customerId"], limit))
        rows = cur.fetchall()
    return [{"orderNo": r[0], "status": r[1], "channel": r[2], "warehouseCode": r[3],
             "paymentType": r[4], "createdAt": r[5], "confirmedAt": r[6]} for r in rows]


@router.get("/orders/{order_no}")
def customer_order(request: Request, order_no: str):
    session = require_customer_session(request)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT id, order_no, customer_id, status, channel, warehouse_code,
                              payment_type, notes, created_at, confirmed_at
                       FROM sales_orders WHERE order_no=%s AND customer_id=%s""",
                    (order_no, session["customerId"]))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Order not found")
        cur.execute("""SELECT product_id, quantity, unit_price
                       FROM sales_order_items WHERE sales_order_id=%s ORDER BY id""", (row[0],))
        items = [{"productId": str(r[0]), "quantity": r[1], "unitPrice": r[2]} for r in cur.fetchall()]
    return {"orderNo": row[1], "customerId": str(row[2]), "status": row[3], "channel": row[4],
            "warehouseCode": row[5], "paymentType": row[6], "notes": row[7],
            "createdAt": row[8], "confirmedAt": row[9], "items": items}
