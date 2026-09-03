-- E.Y.T Order payment mode
-- Credit control is enforced only for genuinely credit-based orders.

ALTER TABLE sales_orders
  ADD COLUMN IF NOT EXISTS payment_type TEXT NOT NULL DEFAULT 'CASH'
  CHECK (payment_type IN ('CASH','CREDIT'));

CREATE INDEX IF NOT EXISTS idx_sales_orders_payment_type
  ON sales_orders(payment_type, status);
