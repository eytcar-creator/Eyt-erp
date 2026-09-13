from __future__ import annotations

import os
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from .auth import require_permission

router = APIRouter(prefix="/api/v1/strategy", tags=["Strategy Users"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


@router.get("/users")
def strategy_users(principal: dict = Depends(require_permission("strategy.write"))):
    """Return active ERP users that can be assigned Strategy actions."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id, username, email
               FROM eyt_users
               WHERE is_active = TRUE
               ORDER BY username"""
        )
        rows = cur.fetchall()
    return {
        "users": [
            {"id": str(row[0]), "username": row[1], "email": row[2]}
            for row in rows
        ]
    }
