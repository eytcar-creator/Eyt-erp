-- E.Y.T ERP | Migration 008 | Invoice payment balance correction
-- PostgreSQL / idempotent
-- Payment allocation legitimately reduces receivable_amount after invoice creation.
BEGIN;

ALTER TABLE invoices
    DROP CONSTRAINT IF EXISTS invoices_check1;

ALTER TABLE invoices
    ADD CONSTRAINT invoices_receivable_balance_check
    CHECK (
        receivable_amount >= 0
        AND receivable_amount <= subtotal - prepayment_amount
    );

COMMIT;
