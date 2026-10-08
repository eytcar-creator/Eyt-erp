CREATE TABLE IF NOT EXISTS rubika_workshop_erp_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workshop_message_id UUID NOT NULL UNIQUE REFERENCES rubika_workshop_messages(id),
    idempotency_key TEXT NOT NULL UNIQUE,
    erp_document_type TEXT NOT NULL,
    erp_document_no TEXT NOT NULL UNIQUE,
    erp_reference_id TEXT,
    status TEXT NOT NULL DEFAULT 'POSTED',
    posted_by UUID,
    posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_rubika_workshop_erp_posts_status
    ON rubika_workshop_erp_posts(status, posted_at DESC);