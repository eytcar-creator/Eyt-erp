-- E.Y.T ERP | Phase 8 KPI, Exception Engine & CEO Control Tower
-- PostgreSQL

CREATE TABLE IF NOT EXISTS kpi_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(80) NOT NULL UNIQUE,
    name_fa VARCHAR(200) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    unit VARCHAR(30) NOT NULL,
    target_value NUMERIC(18,6),
    warning_threshold NUMERIC(18,6),
    critical_threshold NUMERIC(18,6),
    direction VARCHAR(10) NOT NULL DEFAULT 'HIGHER'
        CHECK (direction IN ('HIGHER','LOWER')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kpi_id UUID NOT NULL REFERENCES kpi_definitions(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    actual_value NUMERIC(18,6) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('GREEN','AMBER','RED')),
    source_reference VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (kpi_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS ceo_decision_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_no VARCHAR(80) NOT NULL UNIQUE,
    exception_case_id UUID REFERENCES exception_cases(id),
    decision_type VARCHAR(80) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL'
        CHECK (priority IN ('LOW','NORMAL','HIGH','CRITICAL')),
    title VARCHAR(250) NOT NULL,
    description TEXT NOT NULL,
    recommended_action TEXT,
    amount NUMERIC(18,4),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN','APPROVED','REJECTED','DEFERRED','CLOSED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ,
    decision_note TEXT
);

CREATE TABLE IF NOT EXISTS operational_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_no VARCHAR(80) NOT NULL UNIQUE,
    alert_type VARCHAR(80) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('INFO','WARNING','HIGH','CRITICAL')),
    entity_type VARCHAR(80),
    entity_id UUID,
    message TEXT NOT NULL,
    owner_role_id UUID REFERENCES roles(id),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN','ACKNOWLEDGED','RESOLVED','DISMISSED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_date_status ON kpi_snapshots(snapshot_date, status);
CREATE INDEX IF NOT EXISTS idx_ceo_queue_status_priority ON ceo_decision_queue(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_operational_alerts_status_severity ON operational_alerts(status, severity, created_at);
