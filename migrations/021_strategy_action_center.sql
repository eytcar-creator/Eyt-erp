-- E.Y.T Strategy Action Center persistence
-- Keeps management actions traceable without creating a second KPI/master-data system.

CREATE TABLE IF NOT EXISTS strategy_actions (
    id BIGSERIAL PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL DEFAULT 'STRATEGY_RULE',
    source_ref TEXT,
    priority TEXT NOT NULL CHECK (priority IN ('CRITICAL','HIGH','MEDIUM','INFO')),
    title TEXT NOT NULL,
    reason TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    metric TEXT,
    metric_value NUMERIC,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','IN_PROGRESS','DONE','DISMISSED')),
    assigned_to UUID REFERENCES eyt_users(id) ON DELETE SET NULL,
    due_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result_note TEXT,
    financial_impact NUMERIC NOT NULL DEFAULT 0,
    realized_cash NUMERIC NOT NULL DEFAULT 0,
    realized_profit NUMERIC NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by UUID REFERENCES eyt_users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_strategy_actions_status_priority
    ON strategy_actions(status, priority, due_at);
CREATE INDEX IF NOT EXISTS idx_strategy_actions_assigned_due
    ON strategy_actions(assigned_to, due_at);
CREATE INDEX IF NOT EXISTS idx_strategy_actions_source_type_ref
    ON strategy_actions(source_type, source_ref);

CREATE OR REPLACE FUNCTION strategy_actions_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_strategy_actions_updated_at ON strategy_actions;
CREATE TRIGGER trg_strategy_actions_updated_at
BEFORE UPDATE ON strategy_actions
FOR EACH ROW EXECUTE FUNCTION strategy_actions_touch_updated_at();

-- Dedicated write permission for the Action Center. Existing CEO users receive it.
INSERT INTO eyt_permissions(code)
VALUES ('strategy.write')
ON CONFLICT DO NOTHING;

INSERT INTO eyt_role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM eyt_roles r
CROSS JOIN eyt_permissions p
WHERE r.name = 'CEO' AND p.code = 'strategy.write'
ON CONFLICT DO NOTHING;
