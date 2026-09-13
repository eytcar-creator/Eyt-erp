# Database migrations

Migrations are applied in filename order against PostgreSQL.

## 001_production_core.sql
Creates the production lifecycle tables and indexes used by E.Y.T ERP. It covers production orders, CK45/material lots, operations and subcontractors, QC, production costs, customer prepayments, collections, capital holding cost, traceability, and alerts.

## 021_customer_market_engine.sql
Adds the E.Y.T Customer & Market Engine foundation: consumer profile extensions, customer vehicles, mechanics, parts stores, referrals, installations, purchase history, and repeat-purchase reminders. The intended chain is `Consumer -> Vehicle -> SKU -> Order -> Installation -> Payment -> Repeat Purchase`.

## 023_repeat_purchase_engine.sql
Adds repeat-purchase rules, open-reminder uniqueness, due/overdue indexes, and the `repeat_purchase_opportunities` view used by the CRM.

## 024_repeat_purchase_order_bridge.sql
Adds sales-order traceability for repeat purchases: customer vehicle, source type/id, and source channel. This allows a CRM reminder to create a real sales order while preserving its origin.

## 025_cash_collection_control.sql
Adds invoice/payment source traceability, payment idempotency, and the `cash_collection_control` view for collected and outstanding balances.

## 026_profit_first_dashboard.sql
Adds the initial `profit_first_order_control` view for sales, COGS, gross profit, gross margin, collected cash, outstanding receivables, and operational cash contribution.

## 027_profit_first_cash_realization.sql
Corrects the Profit First control view to calculate outstanding receivables from actual invoice receivables and adds invoice-based cash-realization percentage. This prevents order value from being mistaken for an accounting receivable.

The migrations are intentionally idempotent for the current development phase (`CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`). Production deployment should still record applied migration versions in a dedicated migration ledger before automated releases.
