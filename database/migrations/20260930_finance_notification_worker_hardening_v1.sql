ALTER TABLE finance_notification_outbox
  ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS locked_by VARCHAR(120);

CREATE INDEX IF NOT EXISTS idx_finance_outbox_processing
  ON finance_notification_outbox(status, processing_started_at);

-- Worker contract:
-- PENDING    = available for delivery
-- PROCESSING = exclusively claimed by one worker
-- SENT       = provider accepted delivery
-- FAILED     = terminal failure after retry policy
