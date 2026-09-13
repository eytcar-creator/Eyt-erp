# Database migrations

Migrations are applied in filename order against PostgreSQL.

## 001_production_core.sql
Creates the production lifecycle tables and indexes used by E.Y.T ERP. It covers production orders, CK45/material lots, operations and subcontractors, QC, production costs, customer prepayments, collections, capital holding cost, traceability, and alerts.

## 021_customer_market_engine.sql
Adds the E.Y.T Customer & Market Engine foundation: consumer profile extensions, customer vehicles, mechanics, parts stores, referrals, installations, purchase history, and repeat-purchase reminders. The intended chain is `Consumer -> Vehicle -> SKU -> Order -> Installation -> Payment -> Repeat Purchase`.

The migrations are intentionally idempotent for the current development phase (`CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`). Production deployment should still record applied migration versions in a dedicated migration ledger before automated releases.
