CREATE TABLE IF NOT EXISTS finance_settlement_alerts (
 id BIGSERIAL PRIMARY KEY,
 alert_type VARCHAR(30) NOT NULL,
 entity_type VARCHAR(40) NOT NULL,
 entity_id VARCHAR(120) NOT NULL,
 counterparty_name VARCHAR(255),
 due_at TIMESTAMP,
 outstanding_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
 severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
 status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
 message TEXT NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 resolved_at TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_finance_open_alert
 ON finance_settlement_alerts(alert_type,entity_type,entity_id)
 WHERE status='OPEN';
CREATE INDEX IF NOT EXISTS idx_finance_alert_due
 ON finance_settlement_alerts(status,due_at);