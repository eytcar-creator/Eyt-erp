-- E.Y.T Innovation / Idea Engine v1
-- Migration 031
-- observation -> idea -> evaluation -> prototype -> pilot -> standardize -> realized.

CREATE TABLE IF NOT EXISTS eyt_innovation_ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_no BIGSERIAL UNIQUE,
    title TEXT NOT NULL,
    problem_statement TEXT NOT NULL,
    current_process TEXT,
    proposed_solution TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('PRODUCT','PACKAGING','PRODUCTION','WAREHOUSE','SALES','CUSTOMER_EXPERIENCE','QUALITY','AUTOMATION','COST_REDUCTION','OTHER')),
    source_type TEXT NOT NULL DEFAULT 'INTERNAL' CHECK (source_type IN ('INTERNAL','CUSTOMER','SUPPLIER','MARKET','COMPETITOR','OBSERVATION','OTHER')),
    submitted_by UUID REFERENCES eyt_users(id) ON DELETE SET NULL,
    owner_user_id UUID REFERENCES eyt_users(id) ON DELETE SET NULL,
    stage TEXT NOT NULL DEFAULT 'IDEA' CHECK (stage IN ('IDEA','SCREENING','EVALUATION','PROTOTYPE','PILOT','STANDARDIZE','REALIZED','REJECTED')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','ON_HOLD','DONE','REJECTED')),
    customer_value_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (customer_value_score BETWEEN 0 AND 100),
    financial_impact_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (financial_impact_score BETWEEN 0 AND 100),
    feasibility_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (feasibility_score BETWEEN 0 AND 100),
    strategic_fit_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (strategic_fit_score BETWEEN 0 AND 100),
    effort_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (effort_score BETWEEN 0 AND 100),
    risk_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100),
    priority_score NUMERIC(7,2) NOT NULL DEFAULT 0,
    estimated_annual_revenue NUMERIC(20,2) NOT NULL DEFAULT 0,
    estimated_annual_cost_saving NUMERIC(20,2) NOT NULL DEFAULT 0,
    estimated_annual_time_saving_hours NUMERIC(20,2) NOT NULL DEFAULT 0,
    estimated_implementation_cost NUMERIC(20,2) NOT NULL DEFAULT 0,
    actual_implementation_cost NUMERIC(20,2) NOT NULL DEFAULT 0,
    realized_annual_revenue NUMERIC(20,2) NOT NULL DEFAULT 0,
    realized_annual_cost_saving NUMERIC(20,2) NOT NULL DEFAULT 0,
    realized_annual_time_saving_hours NUMERIC(20,2) NOT NULL DEFAULT 0,
    baseline_metric_value NUMERIC(20,4),
    realized_metric_value NUMERIC(20,4),
    metric_unit TEXT,
    expected_benefit TEXT,
    test_plan TEXT,
    rejection_reason TEXT,
    realized_result_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    evaluated_at TIMESTAMPTZ,
    pilot_started_at TIMESTAMPTZ,
    realized_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS eyt_innovation_events (
    id BIGSERIAL PRIMARY KEY,
    idea_id UUID NOT NULL REFERENCES eyt_innovation_ideas(id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES eyt_users(id) ON DELETE SET NULL,
    from_stage TEXT,
    to_stage TEXT,
    action TEXT NOT NULL,
    note TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eyt_innovation_stage_priority ON eyt_innovation_ideas(stage,status,priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_eyt_innovation_owner ON eyt_innovation_ideas(owner_user_id,stage);
CREATE INDEX IF NOT EXISTS idx_eyt_innovation_category ON eyt_innovation_ideas(category,source_type);
CREATE INDEX IF NOT EXISTS idx_eyt_innovation_events_idea ON eyt_innovation_events(idea_id,created_at DESC);

CREATE OR REPLACE FUNCTION eyt_innovation_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_eyt_innovation_updated_at ON eyt_innovation_ideas;
CREATE TRIGGER trg_eyt_innovation_updated_at BEFORE UPDATE ON eyt_innovation_ideas
FOR EACH ROW EXECUTE FUNCTION eyt_innovation_touch_updated_at();

CREATE OR REPLACE FUNCTION eyt_innovation_priority(p_customer numeric,p_financial numeric,p_feasibility numeric,p_strategy numeric,p_effort numeric,p_risk numeric)
RETURNS numeric LANGUAGE sql IMMUTABLE AS $$
SELECT ROUND((COALESCE(p_customer,0)*0.20)+(COALESCE(p_financial,0)*0.25)+(COALESCE(p_feasibility,0)*0.20)+(COALESCE(p_strategy,0)*0.20)+((100-COALESCE(p_effort,0))*0.10)+((100-COALESCE(p_risk,0))*0.05),2);
$$;

INSERT INTO eyt_permissions(code) VALUES ('innovation.submit'),('innovation.manage') ON CONFLICT DO NOTHING;

INSERT INTO eyt_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM eyt_roles r CROSS JOIN eyt_permissions p
WHERE r.name='CEO' AND p.code IN ('innovation.submit','innovation.manage') ON CONFLICT DO NOTHING;

INSERT INTO eyt_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM eyt_roles r CROSS JOIN eyt_permissions p
WHERE r.name IN ('MANAGER','ADMIN') AND p.code='innovation.submit' ON CONFLICT DO NOTHING;
