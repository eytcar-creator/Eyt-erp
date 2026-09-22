-- E.Y.T ERP | Migration 041 | CRM interaction activity
BEGIN;

CREATE TABLE IF NOT EXISTS eyt_crm_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES eyt_network_entities(id) ON DELETE CASCADE,
    event_id UUID REFERENCES eyt_automation_events(id) ON DELETE SET NULL,
    channel_code VARCHAR(50) NOT NULL,
    activity_type VARCHAR(80) NOT NULL,
    action_code VARCHAR(120),
    provider_message_id VARCHAR(300),
    outcome VARCHAR(40) NOT NULL DEFAULT 'SUCCESS',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_eyt_crm_activities_entity
    ON eyt_crm_activities(entity_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_eyt_crm_activities_event
    ON eyt_crm_activities(event_id);

COMMIT;
