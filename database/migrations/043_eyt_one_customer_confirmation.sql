-- E.Y.T ERP | Migration 043 | E.Y.T One customer confirmation contract
-- Adds auditable, idempotent confirmation metadata to channel intakes.
BEGIN;

ALTER TABLE channel_intakes
  ADD COLUMN IF NOT EXISTS proposal_fingerprint VARCHAR(64),
  ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS confirmation_id VARCHAR(200),
  ADD COLUMN IF NOT EXISTS confirmation_source VARCHAR(80),
  ADD COLUMN IF NOT EXISTS confirmation_actor VARCHAR(200);

CREATE UNIQUE INDEX IF NOT EXISTS uq_channel_intakes_confirmation_id
  ON channel_intakes(confirmation_id)
  WHERE confirmation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_channel_intakes_proposal_fingerprint
  ON channel_intakes(proposal_fingerprint);

COMMIT;
