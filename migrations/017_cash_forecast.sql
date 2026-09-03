-- E.Y.T Profit First: near-term cash forecast and management actions

CREATE OR REPLACE VIEW cash_forecast_30d AS
WITH daily_inflows AS (
  SELECT payment_date::date AS day, SUM(amount) AS inflow
  FROM payments
  WHERE status='POSTED'
    AND payment_date::date BETWEEN CURRENT_DATE AND CURRENT_DATE + 30
  GROUP BY payment_date::date
), daily_outflows AS (
  SELECT transaction_date::date AS day, SUM(amount) AS outflow
  FROM cash_transactions
  WHERE type='OUTFLOW'
    AND transaction_date::date BETWEEN CURRENT_DATE AND CURRENT_DATE + 30
  GROUP BY transaction_date::date
), days AS (
  SELECT generate_series(CURRENT_DATE, CURRENT_DATE + 30, interval '1 day')::date AS day
), opening AS (
  SELECT COALESCE(SUM(CASE WHEN type='INFLOW' THEN amount ELSE -amount END),0) AS balance
  FROM cash_transactions
)
SELECT
  d.day,
  COALESCE(i.inflow,0) AS expected_inflow,
  COALESCE(o.outflow,0) AS expected_outflow,
  op.balance
    + SUM(COALESCE(i.inflow,0)-COALESCE(o.outflow,0)) OVER (ORDER BY d.day) AS projected_cash
FROM days d
CROSS JOIN opening op
LEFT JOIN daily_inflows i ON i.day=d.day
LEFT JOIN daily_outflows o ON o.day=d.day;

CREATE OR REPLACE VIEW action_center AS
SELECT
  'RECEIVABLE' AS action_type,
  invoice_id::text AS reference_id,
  'COLLECT_OVERDUE' AS action,
  outstanding AS amount,
  CASE
    WHEN days_overdue >= 60 THEN 'CRITICAL'
    WHEN days_overdue >= 15 THEN 'HIGH'
    ELSE 'MEDIUM'
  END AS priority
FROM receivables
WHERE outstanding > 0 AND days_overdue > 0
UNION ALL
SELECT
  'ORDER' AS action_type,
  order_no AS reference_id,
  'REVIEW_LOW_MARGIN' AS action,
  net_sales AS amount,
  CASE WHEN contribution_margin < 0 THEN 'CRITICAL' ELSE 'HIGH' END AS priority
FROM order_profitability
WHERE net_sales > 0 AND contribution_margin < 0.15;
