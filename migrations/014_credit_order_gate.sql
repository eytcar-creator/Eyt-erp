-- E.Y.T Credit Gate
-- Pre-confirmation credit decision. Financially blocked orders never reserve stock.

CREATE OR REPLACE FUNCTION check_order_credit_gate(
  p_customer_id UUID,
  p_order_amount NUMERIC
)
RETURNS TABLE (
  allowed BOOLEAN,
  credit_status TEXT,
  available_credit NUMERIC,
  reason TEXT
)
LANGUAGE SQL
STABLE
AS $$
  SELECT allowed, credit_status, available_credit, reason
  FROM check_customer_credit(p_customer_id, p_order_amount);
$$;

CREATE TABLE IF NOT EXISTS order_credit_checks (
  id BIGSERIAL PRIMARY KEY,
  order_no TEXT NOT NULL REFERENCES sales_orders(order_no) ON DELETE CASCADE,
  customer_id UUID NOT NULL,
  requested_amount NUMERIC(18,2) NOT NULL CHECK (requested_amount >= 0),
  allowed BOOLEAN NOT NULL,
  credit_status TEXT NOT NULL,
  available_credit NUMERIC(18,2) NOT NULL,
  reason TEXT NOT NULL,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_credit_checks_order
  ON order_credit_checks(order_no, checked_at DESC);
