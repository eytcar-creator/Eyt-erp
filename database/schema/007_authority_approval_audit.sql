-- E.Y.T ERP | Phase 7 Authority, Approval & Audit Engine
-- PostgreSQL

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name_fa VARCHAR(150) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL UNIQUE,
    name_fa VARCHAR(200) NOT NULL,
    module VARCHAR(80) NOT NULL,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'NORMAL'
        CHECK (risk_level IN ('LOW','NORMAL','HIGH','CRITICAL'))
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS approval_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(80) NOT NULL UNIQUE,
    entity_type VARCHAR(80) NOT NULL,
    action VARCHAR(80) NOT NULL,
    min_amount NUMERIC(18,4),
    max_amount NUMERIC(18,4),
    risk_level VARCHAR(20) NOT NULL DEFAULT 'NORMAL'
        CHECK (risk_level IN ('LOW','NORMAL','HIGH','CRITICAL')),
    required_role_id UUID REFERENCES roles(id),
    escalation_role_id UUID REFERENCES roles(id),
    sla_minutes INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_no VARCHAR(80) NOT NULL UNIQUE,
    policy_id UUID NOT NULL REFERENCES approval_policies(id),
    entity_type VARCHAR(80) NOT NULL,
    entity_id UUID NOT NULL,
    requested_by UUID,
    amount NUMERIC(18,4),
    status VARCHAR(25) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','APPROVED','REJECTED','CANCELLED','ESCALATED','EXPIRED')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ,
    decided_by UUID,
    decision_reason TEXT
);

CREATE TABLE IF NOT EXISTS approval_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL CHECK (action IN ('APPROVE','REJECT','ESCALATE','RETURN')),
    actor_id UUID,
    actor_role_id UUID REFERENCES roles(id),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_id UUID,
    action VARCHAR(80) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    reason TEXT,
    ip_address INET,
    correlation_id UUID
);

CREATE TABLE IF NOT EXISTS exception_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_no VARCHAR(80) NOT NULL UNIQUE,
    exception_type VARCHAR(80) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM'
        CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    entity_type VARCHAR(80),
    entity_id UUID,
    owner_role_id UUID REFERENCES roles(id),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN','IN_PROGRESS','RESOLVED','ESCALATED','CLOSED')),
    description TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution TEXT
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON role_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status, requested_at);
CREATE INDEX IF NOT EXISTS idx_approval_requests_entity ON approval_requests(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_approval_actions_request ON approval_actions(approval_request_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_exception_status_severity ON exception_cases(status, severity, due_at);
