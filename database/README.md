# E.Y.T ERP Database

PostgreSQL database layer for E.Y.T ERP.

## Schema v1.0

Migration: `database/schema/001_initial_schema.sql`

The first migration establishes the core entities for:

- Organization, branches, warehouses and locations
- Vehicle Master and product applications
- Product Master, OEM codes and barcodes
- BOM and production routing
- Suppliers and purchasing
- Customers, dealers and sales orders
- Inventory, reservations, batches and transfers
- Production orders and outsourced operations
- Quality inspections and non-conformances
- Installations, warranty and warranty claims

## Design rules

1. UUID is the technical primary key for master and transactional records.
2. SKU, order numbers, batch numbers and barcodes are business identifiers and have their own uniqueness rules.
3. Inventory movements are represented by `inventory_transactions`; corrections should be compensating transactions rather than destructive edits.
4. Product-to-vehicle compatibility is stored in `product_applications`.
5. Outsourced production is represented through `production_operations.contractor_id`.
6. E.Y.T catalog rules are authoritative for product categories and applications.
7. Soft status fields are preferred over physical deletion for business master data.

## Next migrations

- Roles and permissions
- Price lists and customer-specific pricing
- Goods receipts and delivery documents
- Invoices and payments
- Cost accounting
- Audit log
- n8n event/outbox layer
