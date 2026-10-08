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

CREATE INDEX IF NOT EXISTS idx_rubika_workshop_messages_chat
    ON rubika_workshop_messages (chat_id, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_rubika_workshop_messages_status
    ON rubika_workshop_messages (status, received_at ASC);

CREATE INDEX IF NOT EXISTS idx_rubika_workshop_messages_external_id
    ON rubika_workshop_messages (external_message_id);
