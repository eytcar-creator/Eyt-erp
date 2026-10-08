from __future__ import annotations

import os
from uuid import UUID
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .auth import require_permission

router = APIRouter(prefix="/api/v1/org", tags=["Organization Management"])


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


class AssignmentInput(BaseModel):
    user_id: UUID
    position_code: str = Field(min_length=2, max_length=80)
    location_code: str | None = Field(default=None, max_length=80)
    is_primary: bool = True


@router.get("/positions")
def positions(principal: dict = Depends(require_permission("reporting.read"))):
    with _connect() as conn:
        rows = conn.execute(
            """SELECT p.code,p.title_fa,p.mission_fa,p.reports_to_code,p.process_owner,
                      COALESCE(json_agg(json_build_object(
                        'code',k.code,'title',k.title_fa,'metricKey',k.metric_key,
                        'target',k.target_rule,'frequency',k.frequency,'weight',k.weight
                      ) ORDER BY k.code) FILTER (WHERE k.id IS NOT NULL),'[]'::json) AS kpis
               FROM org_positions p
               LEFT JOIN org_kpis k ON k.position_code=p.code AND k.is_active=TRUE
               WHERE p.is_active=TRUE
               GROUP BY p.id
               ORDER BY p.reports_to_code NULLS FIRST,p.code"""
        ).fetchall()
    return {"positions": [
        {"code":r[0],"title":r[1],"mission":r[2],"reportsTo":r[3],
         "processOwner":r[4],"kpis":r[5]} for r in rows
    ]}


@router.get("/assignments")
def assignments(principal: dict = Depends(require_permission("reporting.read"))):
    with _connect() as conn:
        rows = conn.execute(
            """SELECT a.id,a.user_id,u.username,a.position_code,p.title_fa,a.location_code,
                      a.starts_at,a.ends_at,a.is_primary
               FROM org_employee_assignments a
               JOIN eyt_users u ON u.id=a.user_id
               JOIN org_positions p ON p.code=a.position_code
               WHERE a.ends_at IS NULL OR a.ends_at>=CURRENT_DATE
               ORDER BY p.code,u.username"""
        ).fetchall()
    return {"assignments":[
        {"id":str(r[0]),"userId":str(r[1]),"username":r[2],"positionCode":r[3],
         "title":r[4],"locationCode":r[5],"startsAt":r[6].isoformat(),
         "endsAt":r[7].isoformat() if r[7] else None,"isPrimary":r[8]} for r in rows
    ]}


@router.post("/assignments", status_code=201)
def assign(payload: AssignmentInput, principal: dict = Depends(require_permission("admin.roles.manage"))):
    with _connect() as conn:
        if not conn.execute("SELECT 1 FROM eyt_users WHERE id=%s AND is_active=TRUE",(payload.user_id,)).fetchone():
            raise HTTPException(404,"Active user not found")
        if not conn.execute("SELECT 1 FROM org_positions WHERE code=%s AND is_active=TRUE",(payload.position_code,)).fetchone():
            raise HTTPException(404,"Position not found")
        if payload.is_primary:
            conn.execute(
                """UPDATE org_employee_assignments
                   SET is_primary=FALSE
                   WHERE user_id=%s AND (ends_at IS NULL OR ends_at>=CURRENT_DATE)""",
                (payload.user_id,),
            )
        row=conn.execute(
            """INSERT INTO org_employee_assignments(user_id,position_code,location_code,is_primary)
               VALUES(%s,%s,%s,%s) RETURNING id""",
            (payload.user_id,payload.position_code,payload.location_code,payload.is_primary),
        ).fetchone()
        conn.commit()
    return {"id":str(row[0]),"status":"assigned","positionCode":payload.position_code}


@router.get("/sod-rules")
def sod_rules(principal: dict = Depends(require_permission("reporting.read"))):
    with _connect() as conn:
        rows=conn.execute(
            "SELECT rule_code,title_fa,description_fa,risk_level FROM org_sod_rules WHERE is_active=TRUE ORDER BY risk_level DESC,rule_code"
        ).fetchall()
    return {"rules":[{"code":r[0],"title":r[1],"description":r[2],"risk":r[3]} for r in rows]}
