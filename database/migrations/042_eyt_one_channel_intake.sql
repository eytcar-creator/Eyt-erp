-- E.Y.T ERP | Migration 042 | E.Y.T One channel intake
-- Idempotent PostgreSQL migration for the central channel gateway.
BEGIN;

CREATE TABLE IF NOT EXISTS channel_intakes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel VARCHAR(40) NOT NULL,
  external_message_id VARCHAR(200),
  idempotency_key VARCHAR(200),
  customer_id UUID REFERENCES customers(id),
  raw_text TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  status VARCHAR(40) NOT NULL DEFAULT 'RECEIVED'
    CHECK (status IN ('RECEIVED','PENDING_CONFIRMATION','CONVERTED','REJECTED')),
  order_no VARCHAR(60),
  validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_channel_intakes_idempotency
  ON channel_intakes(idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_channel_intakes_channel_external
  ON channel_intakes(channel, external_message_id)
  WHERE external_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_channel_intakes_status_created
  ON channel_intakes(status, created_at DESC);

COMMIT;
