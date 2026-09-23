from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .auth import require_permission

router = APIRouter(prefix="/api/v1/performance/control", tags=["performance-control"])

EventType = Literal["DOWNTIME", "MATERIAL_SHORTAGE", "ORDER_DELAY", "OTHER"]


def _connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    return psycopg.connect(url)


class DailyPlanInput(BaseModel):
    planDate: date
    locationCode: str = Field(min_length=1, max_length=80)
    employeeCode: str | None = Field(default=None, max_length=100)
    operationCode: str | None = Field(default=None, max_length=100)
    workCenter: str | None = Field(default=None, max_length=120)
    productionOrderId: str | None = None
    productCode: str | None = Field(default=None, max_length=120)
    plannedQty: Decimal = Field(default=Decimal("0"), ge=0)
    plannedHours: Decimal = Field(default=Decimal("0"), ge=0)
    priority: int = Field(default=100, ge=0, le=1000)
    notes: str | None = None


class ControlEventInput(BaseModel):
    eventDate: date
    locationCode: str = Field(min_length=1, max_length=80)
    employeeCode: str | None = Field(default=None, max_length=100)
    eventType: EventType
    operationCode: str | None = Field(default=None, max_length=100)
    productionOrderId: str | None = None
    minutes: int = Field(default=0, ge=0)
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    reasonCode: str | None = Field(default=None, max_length=80)
    notes: str | None = None


@router.post("/plans")
def create_daily_plan(
    payload: DailyPlanInput,
    principal: dict = Depends(require_permission("production.plan")),
):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO performance_daily_plans
              (plan_date, location_code, employee_code, operation_code,
               work_center, production_order_id, product_code, planned_qty,
               planned_hours, priority, notes, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                payload.planDate, payload.locationCode, payload.employeeCode,
                payload.operationCode, payload.workCenter, payload.productionOrderId,
                payload.productCode, payload.plannedQty, payload.plannedHours,
                payload.priority, payload.notes, principal["username"],
            ),
        )
        plan_id = cur.fetchone()[0]
    return {"id": str(plan_id), "status": "PLANNED"}


@router.post("/events")
def create_control_event(
    payload: ControlEventInput,
    principal: dict = Depends(require_permission("production.execute")),
):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO performance_control_events
              (event_date, location_code, employee_code, event_type,
               operation_code, production_order_id, minutes, quantity,
               reason_code, notes, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                payload.eventDate, payload.locationCode, payload.employeeCode,
                payload.eventType, payload.operationCode, payload.productionOrderId,
                payload.minutes, payload.quantity, payload.reasonCode,
                payload.notes, principal["username"],
            ),
        )
        event_id = cur.fetchone()[0]
    return {"id": str(event_id), "status": "RECORDED"}


@router.get("/daily")
def daily_control(
    reportDate: date = Query(...),
    locationCode: str | None = Query(None),
    principal: dict = Depends(require_permission("reporting.read")),
):
    location_filter_plan = "AND p.location_code = %s" if locationCode else ""
    location_filter_event = "AND e.location_code = %s" if locationCode else ""
    location_filter_op = "AND p.location_code = %s" if locationCode else ""

    with _connect() as conn, conn.cursor() as cur:
        params_plan = [reportDate] + ([locationCode] if locationCode else [])
        cur.execute(
            f"""
            SELECT COALESCE(SUM(planned_qty),0),
                   COALESCE(SUM(planned_hours),0),
                   COUNT(*)
            FROM performance_daily_plans p
            WHERE p.plan_date = %s {location_filter_plan}
              AND p.status <> 'CANCELLED'
            """,
            params_plan,
        )
        plan_qty, plan_hours, plan_rows = cur.fetchone()

        params_op = [reportDate, reportDate] + ([locationCode] if locationCode else [])
        cur.execute(
            f"""
            SELECT
              COALESCE(SUM(o.accepted_qty),0),
              COALESCE(SUM(o.rejected_qty),0),
              COALESCE(SUM(o.waste_qty),0),
              COALESCE(SUM(o.service_cost + o.transport_cost),0),
              COUNT(*),
              COALESCE(SUM(EXTRACT(EPOCH FROM (o.actual_end-o.actual_start)))/3600,0)
            FROM production_operations o
            JOIN production_orders po ON po.id=o.production_order_id
            LEFT JOIN performance_daily_plans p
              ON p.production_order_id=po.id
             AND p.plan_date=%s
            WHERE o.status='completed'
              AND o.actual_end >= %s
              AND o.actual_end < %s + INTERVAL '1 day'
              {location_filter_op}
            """,
            [reportDate, reportDate, reportDate] + ([locationCode] if locationCode else []),
        )
        accepted, rejected, waste, operation_cost, operation_rows, actual_hours = cur.fetchone()

        params_events = [reportDate] + ([locationCode] if locationCode else [])
        cur.execute(
            f"""
            SELECT event_type, COALESCE(SUM(minutes),0), COALESCE(SUM(quantity),0), COUNT(*)
            FROM performance_control_events e
            WHERE e.event_date=%s {location_filter_event}
            GROUP BY event_type
            """,
            params_events,
        )
        events = cur.fetchall()

        cur.execute(
            f"""
            SELECT COALESCE(employee_code,'unassigned'),
                   COALESCE(SUM(planned_qty),0)
            FROM performance_daily_plans
            WHERE plan_date=%s {location_filter_plan}
              AND status <> 'CANCELLED'
            GROUP BY 1
            ORDER BY 1
            """,
            params_plan,
        )
        by_employee_plan = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute(
            f"""
            SELECT COALESCE(o.performed_by,'unassigned'),
                   COALESCE(SUM(o.accepted_qty),0),
                   COALESCE(SUM(o.input_qty),0),
                   COALESCE(SUM(o.waste_qty),0),
                   COALESCE(SUM(EXTRACT(EPOCH FROM (o.actual_end-o.actual_start)))/3600,0)
            FROM production_operations o
            JOIN production_orders po ON po.id=o.production_order_id
            WHERE o.status='completed'
              AND o.actual_end >= %s
              AND o.actual_end < %s + INTERVAL '1 day'
            GROUP BY 1
            ORDER BY 1
            """,
            [reportDate, reportDate],
        )
        by_employee_actual = cur.fetchall()

    event_summary = [
        {"type": r[0], "minutes": r[1], "quantity": r[2], "count": r[3]}
        for r in events
    ]
    employee_codes = sorted(set(by_employee_plan) | {r[0] for r in by_employee_actual})
    actual_map = {r[0]: r for r in by_employee_actual}
    employee_rows = []
    for employee in employee_codes:
        r = actual_map.get(employee)
        actual_qty = r[1] if r else 0
        input_qty = r[2] if r else 0
        employee_rows.append({
            "employeeCode": employee,
            "plannedQty": by_employee_plan.get(employee, 0),
            "acceptedQty": actual_qty,
            "achievementPct": float(actual_qty) / float(by_employee_plan.get(employee, 0)) * 100
                if by_employee_plan.get(employee, 0) else None,
            "qualityRatePct": float(actual_qty) / float(input_qty) * 100 if input_qty else None,
            "wasteQty": r[3] if r else 0,
            "actualHours": r[4] if r else 0,
        })

    achievement = float(accepted) / float(plan_qty) * 100 if plan_qty else None
    alerts = []
    if plan_qty and accepted < plan_qty:
        alerts.append({"code": "OUTPUT_BELOW_PLAN", "severity": "warning"})
    if rejected or waste:
        alerts.append({"code": "QUALITY_OR_WASTE", "severity": "warning"})
    if any(r[0] == "MATERIAL_SHORTAGE" and r[1] > 0 for r in events):
        alerts.append({"code": "MATERIAL_SHORTAGE", "severity": "critical"})
    if any(r[0] == "DOWNTIME" and r[1] >= 60 for r in events):
        alerts.append({"code": "DOWNTIME_OVER_60_MIN", "severity": "critical"})

    return {
        "date": reportDate,
        "locationCode": locationCode,
        "plan": {
            "rows": plan_rows,
            "plannedQty": plan_qty,
            "plannedHours": plan_hours,
        },
        "actual": {
            "operationRows": operation_rows,
            "acceptedQty": accepted,
            "rejectedQty": rejected,
            "wasteQty": waste,
            "operationCost": operation_cost,
            "actualHours": actual_hours,
        },
        "achievementPct": achievement,
        "events": event_summary,
        "employees": employee_rows,
        "alerts": alerts,
        "formula": {
            "achievementPct": "acceptedQty / plannedQty * 100",
            "qualityRatePct": "acceptedQty / inputQty * 100",
            "primaryOutput": "QC-approved good output remains the management output target",
        },
    }
