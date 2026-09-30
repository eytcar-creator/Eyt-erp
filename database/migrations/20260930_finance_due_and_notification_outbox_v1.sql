ALTER TABLE invoices ADD COLUMN IF NOT EXISTS due_at TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_invoices_due_at ON invoices(due_at);
CREATE TABLE IF NOT EXISTS finance_notification_outbox (
 id BIGSERIAL PRIMARY KEY,
 event_type VARCHAR(60) NOT NULL,
 entity_type VARCHAR(60) NOT NULL,
 entity_id VARCHAR(120) NOT NULL,
 payload JSONB NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
 attempts INTEGER NOT NULL DEFAULT 0,
 available_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 sent_at TIMESTAMP,
 last_error TEXT,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_finance_outbox_pending
 ON finance_notification_outbox(status,available_at);