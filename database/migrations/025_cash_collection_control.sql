-- E.Y.T ERP | Migration 025 | Cash collection control
-- Links invoices/payments to order origin and prevents duplicate payment references.
BEGIN;

ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(40),
    ADD COLUMN IF NOT EXISTS source_id UUID;

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(160);

CREATE UNIQUE INDEX IF NOT EXISTS ux_payments_idempotency_key
    ON payments(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_invoices_source
    ON invoices(source_type, source_id);

CREATE OR REPLACE VIEW cash_collection_control AS
SELECT
    i.id AS invoice_id,
    i.invoice_no,
    i.sales_order_id,
    i.customer_id,
    i.invoice_date,
    i.subtotal,
    i.prepayment_amount,
    i.receivable_amount,
    COALESCE(SUM(pa.amount), 0) AS collected,
    GREATEST(i.receivable_amount - COALESCE(SUM(pa.amount), 0), 0) AS outstanding,
    CASE
      WHEN GREATEST(i.receivable_amount - COALESCE(SUM(pa.amount), 0), 0) = 0 THEN 'PAID'
      WHEN COALESCE(SUM(pa.amount), 0) > 0 THEN 'PARTIALLY_PAID'
      ELSE 'UNPAID'
    END AS collection_status
FROM invoices i
LEFT JOIN payment_allocations pa ON pa.invoice_id = i.id
WHERE i.status <> 'VOID'
GROUP BY i.id, i.invoice_no, i.sales_order_id, i.customer_id,
         i.invoice_date, i.subtotal, i.prepayment_amount, i.receivable_amount;

COMMIT;
