-- E.Y.T contractor payment ledger.
CREATE TABLE IF NOT EXISTS production_payments (
 id BIGSERIAL PRIMARY KEY,
 payable_id BIGINT NOT NULL REFERENCES production_service_payables(id),
 amount NUMERIC(16,2) NOT NULL CHECK(amount>0),
 payment_method VARCHAR(40) NOT NULL,
 reference_no VARCHAR(100),
 paid_by VARCHAR(100) NOT NULL,
 paid_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 notes TEXT
);
CREATE INDEX IF NOT EXISTS ix_production_payments_payable ON production_payments(payable_id,paid_at);
