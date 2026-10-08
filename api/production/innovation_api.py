"""E.Y.T Innovation / Idea Engine API."""
from __future__ import annotations
import os
from decimal import Decimal
from typing import Literal
from uuid import UUID
import psycopg
from psycopg.types.json import Json
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from .auth import require_permission

router=APIRouter(prefix="/api/v1/innovation",tags=["Innovation / Idea Engine"])
def _connect():
    url=os.getenv("DATABASE_URL")
    if not url: raise HTTPException(503,"DATABASE_URL is not configured")
    return psycopg.connect(url)

Category=Literal["PRODUCT","PACKAGING","PRODUCTION","WAREHOUSE","SALES","CUSTOMER_EXPERIENCE","QUALITY","AUTOMATION","COST_REDUCTION","OTHER"]
Stage=Literal["IDEA","SCREENING","EVALUATION","PROTOTYPE","PILOT","STANDARDIZE","REALIZED","REJECTED"]

class IdeaCreate(BaseModel):
    title:str=Field(min_length=3,max_length=300)
    problem_statement:str=Field(min_length=5,max_length=5000)
    current_process:str|None=Field(default=None,max_length=5000)
    proposed_solution:str=Field(min_length=5,max_length=5000)
    category:Category="OTHER"
    source_type:Literal["INTERNAL","CUSTOMER","SUPPLIER","MARKET","COMPETITOR","OBSERVATION","OTHER"]="INTERNAL"
    owner_user_id:UUID|None=None
    expected_benefit:str|None=Field(default=None,max_length=5000)
    test_plan:str|None=Field(default=None,max_length=5000)
    estimated_annual_revenue:Decimal=Decimal("0")
    estimated_annual_cost_saving:Decimal=Decimal("0")
    estimated_annual_time_saving_hours:Decimal=Decimal("0")
    estimated_implementation_cost:Decimal=Decimal("0")
    baseline_metric_value:Decimal|None=None
    metric_unit:str|None=Field(default=None,max_length=100)

class IdeaUpdate(BaseModel):
    title:str|None=Field(default=None,min_length=3,max_length=300)
    owner_user_id:UUID|None=None
    expected_benefit:str|None=Field(default=None,max_length=5000)
    test_plan:str|None=Field(default=None,max_length=5000)
    current_process:str|None=Field(default=None,max_length=5000)
    proposed_solution:str|None=Field(default=None,max_length=5000)
    status:Literal["OPEN","ON_HOLD","DONE","REJECTED"]|None=None

class ScoreUpdate(BaseModel):
    customer_value_score:Decimal=Field(ge=0,le=100)
    financial_impact_score:Decimal=Field(ge=0,le=100)
    feasibility_score:Decimal=Field(ge=0,le=100)
    strategic_fit_score:Decimal=Field(ge=0,le=100)
    effort_score:Decimal=Field(ge=0,le=100)
    risk_score:Decimal=Field(ge=0,le=100)

class Advance(BaseModel):
    to_stage:Stage
    note:str|None=Field(default=None,max_length=5000)

class Realize(BaseModel):
    realized_annual_revenue:Decimal=Decimal("0")
    realized_annual_cost_saving:Decimal=Decimal("0")
    realized_annual_time_saving_hours:Decimal=Decimal("0")
    actual_implementation_cost:Decimal=Decimal("0")
    realized_metric_value:Decimal|None=None
    realized_result_note:str=Field(min_length=3,max_length=5000)

_SELECT="""SELECT id,idea_no,title,problem_statement,current_process,proposed_solution,category,source_type,submitted_by,owner_user_id,stage,status,customer_value_score,financial_impact_score,feasibility_score,strategic_fit_score,effort_score,risk_score,priority_score,estimated_annual_revenue,estimated_annual_cost_saving,estimated_annual_time_saving_hours,estimated_implementation_cost,actual_implementation_cost,realized_annual_revenue,realized_annual_cost_saving,realized_annual_time_saving_hours,baseline_metric_value,realized_metric_value,metric_unit,expected_benefit,test_plan,rejection_reason,realized_result_note,created_at,updated_at,evaluated_at,pilot_started_at,realized_at FROM eyt_innovation_ideas"""

def _row(r):
    keys=["id","ideaNo","title","problemStatement","currentProcess","proposedSolution","category","sourceType","submittedBy","ownerUserId","stage","status","customerValueScore","financialImpactScore","feasibilityScore","strategicFitScore","effortScore","riskScore","priorityScore","estimatedAnnualRevenue","estimatedAnnualCostSaving","estimatedAnnualTimeSavingHours","estimatedImplementationCost","actualImplementationCost","realizedAnnualRevenue","realizedAnnualCostSaving","realizedAnnualTimeSavingHours","baselineMetricValue","realizedMetricValue","metricUnit","expectedBenefit","testPlan","rejectionReason","realizedResultNote","createdAt","updatedAt","evaluatedAt","pilotStartedAt","realizedAt"]
    out=dict(zip(keys,r))
    for k in ("createdAt","updatedAt","evaluatedAt","pilotStartedAt","realizedAt"): out[k]=out[k].isoformat() if out[k] else None
    return out

@router.post("/ideas",status_code=201)
def create_idea(payload:IdeaCreate,request:Request,principal:dict=Depends(require_permission("innovation.submit"))):
    with _connect() as conn,conn.cursor() as cur:
        cur.execute("""INSERT INTO eyt_innovation_ideas(title,problem_statement,current_process,proposed_solution,category,source_type,submitted_by,owner_user_id,expected_benefit,test_plan,estimated_annual_revenue,estimated_annual_cost_saving,estimated_annual_time_saving_hours,estimated_implementation_cost,baseline_metric_value,metric_unit)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",(payload.title,payload.problem_statement,payload.current_process,payload.proposed_solution,payload.category,payload.source_type,principal["id"],payload.owner_user_id,payload.expected_benefit,payload.test_plan,payload.estimated_annual_revenue,payload.estimated_annual_cost_saving,payload.estimated_annual_time_saving_hours,payload.estimated_implementation_cost,payload.baseline_metric_value,payload.metric_unit))
        idea_id=cur.fetchone()[0]
        cur.execute("INSERT INTO eyt_innovation_events(idea_id,actor_user_id,to_stage,action,note) VALUES(%s,%s,'IDEA','CREATED','Idea submitted')",(idea_id,principal["id"]))
        conn.commit()
        cur.execute(_SELECT+" WHERE id=%s",(idea_id,))
        return _row(cur.fetchone())

@router.get("/ideas")
def list_ideas(stage:Stage|None=Query(None),category:Category|None=Query(None),status:str|None=Query(None),limit:int=Query(50,ge=1,le=200),principal:dict=Depends(require_permission("innovation.submit"))):
    with _connect() as conn,conn.cursor() as cur:
        clauses=[];params=[]
        if stage: clauses.append("stage=%s");params.append(stage)
        if category: clauses.append("category=%s");params.append(category)
        if status: clauses.append("status=%s");params.append(status)
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        cur.execute(_SELECT+where+" ORDER BY priority_score DESC,created_at DESC LIMIT %s",params+[limit])
        return {"ideas":[_row(x) for x in cur.fetchall()]}

@router.get("/ideas/{idea_id}")
def get_idea(idea_id:UUID,principal:dict=Depends(require_permission("innovation.submit"))):
    with _connect() as conn,conn.cursor() as cur:
        cur.execute(_SELECT+" WHERE id=%s",(idea_id,));row=cur.fetchone()
        if not row: raise HTTPException(404,"Idea not found")
        cur.execute("SELECT id,from_stage,to_stage,action,note,created_at FROM eyt_innovation_events WHERE idea_id=%s ORDER BY created_at",(idea_id,))
        events=[{"id":x[0],"fromStage":x[1],"toStage":x[2],"action":x[3],"note":x[4],"createdAt":x[5].isoformat()} for x in cur.fetchall()]
    item=_row(row);item["events"]=events;return item

@router.patch("/ideas/{idea_id}")
def update_idea(idea_id:UUID,payload:IdeaUpdate,request:Request,principal:dict=Depends(require_permission("innovation.manage"))):
    values={k:v for k,v in payload.model_dump().items() if v is not None}
    if not values: raise HTTPException(400,"No fields supplied")
    with _connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT id FROM eyt_innovation_ideas WHERE id=%s FOR UPDATE",(idea_id,))
        if not cur.fetchone(): raise HTTPException(404,"Idea not found")
        sets=[];params=[]
        for k,v in values.items(): sets.append(f"{k}=%s");params.append(v)
        params.append(idea_id);cur.execute(f"UPDATE eyt_innovation_ideas SET {','.join(sets)} WHERE id=%s",params);conn.commit()
    return get_idea(idea_id,principal)

@router.post("/ideas/{idea_id}/score")
def score_idea(idea_id:UUID,payload:ScoreUpdate,request:Request,principal:dict=Depends(require_permission("innovation.manage"))):
    vals=list(payload.model_dump().values())
    with _connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT stage FROM eyt_innovation_ideas WHERE id=%s FOR UPDATE",(idea_id,));row=cur.fetchone()
        if not row: raise HTTPException(404,"Idea not found")
        cur.execute("""UPDATE eyt_innovation_ideas SET customer_value_score=%s,financial_impact_score=%s,feasibility_score=%s,strategic_fit_score=%s,effort_score=%s,risk_score=%s,priority_score=eyt_innovation_priority(%s,%s,%s,%s,%s,%s),evaluated_at=COALESCE(evaluated_at,now()) WHERE id=%s""",vals+vals+[idea_id])
        cur.execute("INSERT INTO eyt_innovation_events(idea_id,actor_user_id,from_stage,to_stage,action,note) VALUES(%s,%s,%s,%s,'SCORED','Priority score recalculated')",(idea_id,principal["id"],row[0],row[0]));conn.commit()
    return get_idea(idea_id,principal)

@router.post("/ideas/{idea_id}/advance")
def advance_idea(idea_id:UUID,payload:Advance,request:Request,principal:dict=Depends(require_permission("innovation.manage"))):
    with _connect() as conn,conn.cursor() as cur:
        cur.execute("SELECT stage FROM eyt_innovation_ideas WHERE id=%s FOR UPDATE",(idea_id,));row=cur.fetchone()
        if not row: raise HTTPException(404,"Idea not found")
        old=row[0]
        cur.execute("""UPDATE eyt_innovation_ideas SET stage=%s,status=CASE WHEN %s='REJECTED' THEN 'REJECTED' WHEN %s='REALIZED' THEN 'DONE' ELSE status END,realized_at=CASE WHEN %s='REALIZED' THEN now() ELSE realized_at END,pilot_started_at=CASE WHEN %s='PILOT' THEN COALESCE(pilot_started_at,now()) ELSE pilot_started_at END WHERE id=%s""",(payload.to_stage,payload.to_stage,payload.to_stage,payload.to_stage,payload.to_stage,idea_id))
        cur.execute("INSERT INTO eyt_innovation_events(idea_id,actor_user_id,from_stage,to_stage,action,note) VALUES(%s,%s,%s,%s,'STAGE_CHANGED',%s)",(idea_id,principal["id"],old,payload.to_stage,payload.note));conn.commit()
    return get_idea(idea_id,principal)

@router.post("/ideas/{idea_id}/realize")
def realize_idea(idea_id:UUID,payload:Realize,request:Request,principal:dict=Depends(require_permission("innovation.manage"))):
    with _connect() as conn,conn.cursor() as cur:
        cur.execute("""UPDATE eyt_innovation_ideas SET stage='REALIZED',status='DONE',actual_implementation_cost=%s,realized_annual_revenue=%s,realized_annual_cost_saving=%s,realized_annual_time_saving_hours=%s,realized_metric_value=%s,realized_result_note=%s,realized_at=now() WHERE id=%s RETURNING id""",(payload.actual_implementation_cost,payload.realized_annual_revenue,payload.realized_annual_cost_saving,payload.realized_annual_time_saving_hours,payload.realized_metric_value,payload.realized_result_note,idea_id))
        if not cur.fetchone(): raise HTTPException(404,"Idea not found")
        cur.execute("INSERT INTO eyt_innovation_events(idea_id,actor_user_id,to_stage,action,note,metadata) VALUES(%s,%s,'REALIZED','REALIZED',%s,%s)",(idea_id,principal["id"],payload.realized_result_note,Json({"annualValue":str(payload.realized_annual_revenue+payload.realized_annual_cost_saving),"implementationCost":str(payload.actual_implementation_cost)})));conn.commit()
    return get_idea(idea_id,principal)

@router.get("/dashboard")
def dashboard(principal:dict=Depends(require_permission("innovation.submit"))):
    with _connect() as conn,conn.cursor() as cur:
        cur.execute("""SELECT COUNT(*),COUNT(*) FILTER(WHERE stage IN ('IDEA','SCREENING','EVALUATION','PROTOTYPE','STANDARDIZE')),COUNT(*) FILTER(WHERE stage='PILOT'),COUNT(*) FILTER(WHERE stage='REALIZED'),COALESCE(SUM(realized_annual_revenue+realized_annual_cost_saving),0),COALESCE(SUM(actual_implementation_cost),0) FROM eyt_innovation_ideas""")
        total,active,pilots,realized,value,cost=cur.fetchone()
        cur.execute("SELECT category,COUNT(*),COALESCE(SUM(realized_annual_revenue+realized_annual_cost_saving),0) FROM eyt_innovation_ideas GROUP BY category ORDER BY COUNT(*) DESC")
        by_category=[{"category":x[0],"count":x[1],"realizedAnnualValue":x[2]} for x in cur.fetchall()]
    return {"totalIdeas":total,"activeIdeas":active,"pilots":pilots,"realizedIdeas":realized,"realizedAnnualValue":value,"implementationCost":cost,"netAnnualValueAfterCost":value-cost,"byCategory":by_category}
