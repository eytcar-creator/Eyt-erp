-- E.Y.T ERP | Migration 019 | Customer Portal Identity contract
-- Keeps customer portal identity separate from internal ERP users.
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS customer_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
    account_code VARCHAR(60) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','ACTIVE','SUSPENDED','CLOSED')),
    phone VARCHAR(40),
    email VARCHAR(254),
    password_hash TEXT,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_customer_accounts_phone ON customer_accounts(phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_customer_accounts_email ON customer_accounts(email) WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS customer_account_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES customer_accounts(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_customer_account_sessions_account
    ON customer_account_sessions(account_id, expires_at);

CREATE TABLE IF NOT EXISTS customer_account_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES customer_accounts(id) ON DELETE CASCADE,
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(40),
    email VARCHAR(254),
    role VARCHAR(80),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_customer_account_contacts_account
    ON customer_account_contacts(account_id);

ALTER TABLE customers ADD COLUMN IF NOT EXISTS default_price_list_id UUID;

COMMIT;
