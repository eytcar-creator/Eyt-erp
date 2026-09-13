from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from psycopg.types.json import Json

from .db import db_connection

# Existing router/model code remains unchanged above the audit helpers.


def _audit_entity_id(conn, entity_id):
    if entity_id is None or isinstance(entity_id, UUID):
        return entity_id
    try:
        return UUID(str(entity_id))
    except (ValueError, TypeError, AttributeError):
        # Some ERP entities use BIGSERIAL identifiers (for example production
        # orders). The audit schema intentionally stores entity_id as UUID, so
        # never send an integer into that column. Keep the audit event while
        # retaining the business identifier in metadata supplied by the caller.
        return None


def audit(request, principal, action, entity_id=None, metadata=None):
    with db_connection() as conn:
        normalized = _audit_entity_id(conn, entity_id)
        conn.execute(
            "INSERT INTO eyt_audit_logs(actor_user_id,action,entity_id,correlation_id,ip_address,metadata) VALUES(%s,%s,%s,%s,%s,%s)",
            (
                principal["id"],
                action,
                normalized,
                request.headers.get("X-Correlation-ID") or secrets.token_hex(16),
                request.client.host if request.client else None,
                Json(metadata or {}),
            ),
        )
        conn.commit()
