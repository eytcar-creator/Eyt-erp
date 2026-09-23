-- E.Y.T ERP | Migration 039 | Automation event outbox
-- Stable integration boundary for n8n and other automation consumers.
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS eyt_automation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(80) NOT NULL,
    aggregate_id UUID,
    source_table VARCHAR(120),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','PROCESSING','DELIVERED','FAILED','IGNORED')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMPTZ,
    locked_by VARCHAR(120),
    delivered_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_eyt_automation_pending
    ON eyt_automation_events(status, available_at, created_at);

CREATE INDEX IF NOT EXISTS idx_eyt_automation_aggregate
    ON eyt_automation_events(aggregate_type, aggregate_id);

CREATE OR REPLACE FUNCTION eyt_emit_automation_event()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_payload JSONB;
    v_aggregate_id UUID;
    v_event_type TEXT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_payload := to_jsonb(OLD);
    ELSE
        v_payload := to_jsonb(NEW);
    END IF;

    BEGIN
        v_aggregate_id := (v_payload ->> 'id')::uuid;
    EXCEPTION WHEN OTHERS THEN
        v_aggregate_id := NULL;
    END;

    v_event_type := lower(TG_TABLE_NAME || '.' || TG_OP);

    INSERT INTO eyt_automation_events(
        event_type, aggregate_type, aggregate_id, source_table, payload
    )
    VALUES (
        v_event_type,
        TG_TABLE_NAME,
        v_aggregate_id,
        TG_TABLE_NAME,
        jsonb_build_object('operation', TG_OP, 'record', v_payload)
    );

    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_eyt_automation_sales_orders ON sales_orders;
CREATE TRIGGER trg_eyt_automation_sales_orders
AFTER INSERT OR UPDATE OR DELETE ON sales_orders
FOR EACH ROW EXECUTE FUNCTION eyt_emit_automation_event();

DROP TRIGGER IF EXISTS trg_eyt_automation_eyt_network_entities ON eyt_network_entities;
CREATE TRIGGER trg_eyt_automation_eyt_network_entities
AFTER INSERT OR UPDATE OR DELETE ON eyt_network_entities
FOR EACH ROW EXECUTE FUNCTION eyt_emit_automation_event();

DROP TRIGGER IF EXISTS trg_eyt_automation_eyt_service_reminders ON eyt_service_reminders;
CREATE TRIGGER trg_eyt_automation_eyt_service_reminders
AFTER INSERT OR UPDATE OR DELETE ON eyt_service_reminders
FOR EACH ROW EXECUTE FUNCTION eyt_emit_automation_event();

INSERT INTO eyt_permissions(code) VALUES ('automation.read'),('automation.write')
ON CONFLICT (code) DO NOTHING;

INSERT INTO eyt_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM eyt_roles r CROSS JOIN eyt_permissions p
WHERE r.name='CEO' AND p.code IN ('automation.read','automation.write')
ON CONFLICT DO NOTHING;

COMMIT;
