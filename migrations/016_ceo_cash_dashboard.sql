-- E.Y.T CEO Dashboard: cash, receivables, inventory and contribution profit

CREATE OR REPLACE VIEW ceo_cash_position AS
SELECT
  COALESCE(SUM(CASE WHEN type='INFLOW' THEN amount ELSE 0 END),0) AS total_inflow,
  COALESCE(SUM(CASE WHEN type='OUTFLOW' THEN amount ELSE 0 END),0) AS total_outflow,
  COALESCE(SUM(CASE WHEN type='INFLOW' THEN amount ELSE -amount END),0) AS net_cash_movement
FROM cash_transactions;

CREATE OR REPLACE VIEW ceo_receivables AS
SELECT
  COALESCE(SUM(outstanding),0) AS outstanding_receivables,
  COALESCE(SUM(CASE WHEN days_overdue > 0 THEN outstanding ELSE 0 END),0) AS overdue_receivables,
  COALESCE(SUM(CASE WHEN days_overdue >= 60 THEN outstanding ELSE 0 END),0) AS high_risk_receivables
FROM receivables;

CREATE OR REPLACE VIEW ceo_profit AS
SELECT
  COALESCE(SUM(net_sales),0) AS net_sales,
  COALESCE(SUM(contribution_profit),0) AS contribution_profit,
  CASE WHEN COALESCE(SUM(net_sales),0) > 0
       THEN SUM(contribution_profit) / SUM(net_sales) ELSE 0 END AS contribution_margin
FROM order_profitability;

CREATE OR REPLACE VIEW ceo_dashboard AS
SELECT
  c.net_cash_movement,
  r.outstanding_receivables,
  r.overdue_receivables,
  r.high_risk_receivables,
  p.net_sales,
  p.contribution_profit,
  p.contribution_margin,
  NOW() AS generated_at
FROM ceo_cash_position c
CROSS JOIN ceo_receivables r
CROSS JOIN ceo_profit p;
