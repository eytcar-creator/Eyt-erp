# E.Y.T ERP Database Migrations

Migrations are applied in filename order against PostgreSQL.

## Current canonical layers
- 001: Production core
- 006: Sales, invoicing and receivables
- 018: Order Center schema contract
- 021: Customer & Market Engine
- 023: Repeat Purchase Engine
- 024: Repeat Purchase → Sales Order bridge
- 025: Cash collection control
- 026: Profit First operational dashboard
- 027: Profit First invoice bridge

Migration 027 makes the Profit First dashboard use the canonical invoice/payment layer for receivables and collection realization.

## Production rule
Keep a production migration ledger and apply migrations in numeric filename order. Never edit an already-applied migration in production; add the next migration instead.
