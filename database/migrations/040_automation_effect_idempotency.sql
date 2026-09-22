-- E.Y.T ERP | Migration 040 | Automation side-effect idempotency
BEGIN;

CREATE TABLE IF NOT EXISTS eyt_automation_effects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(300) NOT NULL UNIQUE,
    event_id UUID REFERENCES eyt_automation_events(id) ON DELETE SET NULL,
    channel VARCHAR(80) NOT NULL,
    action_code VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PROCESSING'
        CHECK (status IN ('PROCESSING','SENT','FAILED','SKIPPED','DRY_RUN')),
    provider_message_id VARCHAR(300),
    response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_eyt_automation_effects_event
    ON eyt_automation_effects(event_id);

CREATE INDEX IF NOT EXISTS idx_eyt_automation_effects_status
    ON eyt_automation_effects(status, updated_at);

COMMIT;
