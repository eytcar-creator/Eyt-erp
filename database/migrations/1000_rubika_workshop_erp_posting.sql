CREATE TABLE IF NOT EXISTS rubika_workshop_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel TEXT NOT NULL DEFAULT 'RUBIKA_WORKSHOP',
    external_message_id TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    chat_id TEXT,
    sender_id TEXT,
    sender_name TEXT,
    message_text TEXT,
    message_type TEXT NOT NULL DEFAULT 'GENERAL',
    raw_payload JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'RECEIVED',
    processed_at TIMESTAMPTZ,
    processing_error TEXT,
    extracted_data JSONB
);

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
