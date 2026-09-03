-- E.Y.T Credit Control
-- Credit limits, exposure, risk and pre-sale credit checks.

CREATE TABLE IF NOT EXISTS customer_credit_profiles (
  customer_id UUID PRIMARY KEY,
  credit_limit NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
  payment_terms_days INTEGER NOT NULL DEFAULT 0 CHECK (payment_terms_days >= 0),
  risk_level TEXT NOT NULL DEFAULT 'LOW' CHECK (risk_level IN ('LOW','MEDIUM','HIGH','BLOCKED')),
  manual_hold BOOLEAN NOT NULL DEFAULT FALSE,
  notes TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customer_credit_risk
  ON customer_credit_profiles(risk_level, manual_hold);

CREATE OR REPLACE VIEW customer_credit_status AS
SELECT
  c.customer_id,
  c.credit_limit,
  COALESCE(SUM(r.outstanding), 0)::NUMERIC(18,2) AS outstanding_debt,
  COALESCE(SUM(CASE WHEN r.days_overdue > 0 THEN r.outstanding ELSE 0 END), 0)::NUMERIC(18,2) AS overdue_debt,
  GREATEST(c.credit_limit - COALESCE(SUM(r.outstanding), 0), 0)::NUMERIC(18,2) AS available_credit,
  c.payment_terms_days,
  c.risk_level,
  c.manual_hold,
  CASE
    WHEN c.manual_hold OR c.risk_level = 'BLOCKED' THEN 'BLOCKED'
    WHEN COALESCE(SUM(r.outstanding), 0) > c.credit_limit THEN 'CREDIT_HOLD'
    WHEN COALESCE(SUM(CASE WHEN r.days_overdue >= 60 THEN r.outstanding ELSE 0 END), 0) > 0 THEN 'HIGH_RISK'
    WHEN COALESCE(SUM(CASE WHEN r.days_overdue >= 15 THEN r.outstanding ELSE 0 END), 0) > 0 THEN 'REVIEW'
    ELSE 'OK'
  END AS credit_status
FROM customer_credit_profiles c
LEFT JOIN receivables r ON r.customer_id = c.customer_id
GROUP BY c.customer_id, c.credit_limit, c.payment_terms_days,
         c.risk_level, c.manual_hold;

CREATE OR REPLACE FUNCTION check_customer_credit(
  p_customer_id UUID,
  p_order_amount NUMERIC
)
RETURNS TABLE (
  allowed BOOLEAN,
  credit_status TEXT,
  credit_limit NUMERIC,
  outstanding_debt NUMERIC,
  available_credit NUMERIC,
  requested_amount NUMERIC,
  reason TEXT
)
LANGUAGE SQL
STABLE
AS $$
  SELECT
    (s.credit_status = 'OK' AND s.available_credit >= p_order_amount),
    s.credit_status,
    s.credit_limit,
    s.outstanding_debt,
    s.available_credit,
    p_order_amount,
    CASE
      WHEN s.credit_status <> 'OK' THEN s.credit_status
      WHEN s.available_credit < p_order_amount THEN 'CREDIT_LIMIT_EXCEEDED'
      ELSE 'OK'
    END
  FROM customer_credit_status s
  WHERE s.customer_id = p_customer_id;
$$;
