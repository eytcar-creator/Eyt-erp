-- Finance cash control v1: explicit funding source, cash movement and alert ledger.
CREATE TABLE IF NOT EXISTS finance_funding_sources (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(30) NOT NULL,
    account_reference VARCHAR(120),
    opening_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
    current_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
    currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finance_cash_movements (
    id BIGSERIAL PRIMARY KEY,
    movement_no VARCHAR(60) UNIQUE NOT NULL,
    funding_source_id BIGINT NOT NULL REFERENCES finance_funding_sources(id),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('IN','OUT')),
    amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    movement_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reference_type VARCHAR(50),
    reference_id VARCHAR(120),
    counterparty_name VARCHAR(255),
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'POSTED',
    created_by VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finance_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    entity_type VARCHAR(50),
    entity_id VARCHAR(120),
    message TEXT NOT NULL,
    due_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_finance_cash_movements_source_date
ON finance_cash_movements(funding_source_id, movement_date DESC);
CREATE INDEX IF NOT EXISTS idx_finance_alerts_open_due
ON finance_alerts(status, due_at);
