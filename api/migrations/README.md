# E.Y.T ERP Schema Migration Reconciliation

## Migration order

The legacy SQL schema files under `database/schema/` are the source material. They must be reconciled into one deterministic Alembic history before production bootstrap.

Recommended dependency order:

1. Core/master tables: users, roles, permissions, customers, suppliers, products, categories, warehouses.
2. Inventory and transaction tables.
3. Procurement and receiving.
4. Production, BOM, subcontracting and costing.
5. Quality control and exceptions.
6. Sales, invoices, delivery and CRM.
7. Finance journals, payments and receivable aging.
8. Vehicle catalog, fitment, cross-reference and kits.
9. B2B price lists and order requests.
10. Approval, audit, KPI and control-tower tables.
11. Integration/webhook support.

## Reconciliation rules

- A referenced table must exist before its foreign key is created.
- Duplicate table definitions are consolidated into one canonical definition.
- UUID primary keys remain the canonical identifier unless an explicit compatibility requirement exists.
- Foreign keys must use matching UUID types.
- `ON DELETE` behavior must be explicit for dependent data.
- Unique constraints must reflect business identity, not accidental duplicates.
- Monetary values use `NUMERIC`, never floating-point types.
- Dates/times use `DATE` or `TIMESTAMPTZ` according to business meaning.
- Audit and financial records should be append-oriented and must not be silently deleted.

## Known compatibility checks

Before executing the full bootstrap, verify that every table referenced by later phases exists, especially:

- `customers`
- `suppliers`
- `products`
- `sales_invoices`
- `production_orders`
- `roles`
- `exception_cases`

The legacy phase files may currently reference tables whose canonical definitions are located in earlier or not-yet-created migrations. Those dependencies must be resolved rather than bypassed.

## Bootstrap policy

Do not run the legacy SQL files blindly against production. Generate reviewed Alembic revisions from the reconciled schema, execute them against a clean disposable PostgreSQL database, run the API/security tests, then promote the migration set.
