# E.Y.T ERP — Database Migration Chain

The operational database migrations are numbered and must execute in strict ascending order.

## Current chain

1. `001_production_core.sql`
2. `002_production_indexes.sql`
3. `003_identity_rbac.sql`
4. `004_product_master_inventory.sql`
5. `005_purchase_receiving.sql`

## Release rule

Every new migration must:

- use the next three-digit sequence number;
- be committed as a single ordered SQL migration;
- pass `python scripts/verify_migration_chain.py`;
- be executed with PostgreSQL `ON_ERROR_STOP=1` in CI;
- preserve the existing migrations rather than rewriting history.

The verifier intentionally checks only deterministic file ordering and numbering. SQL execution remains the responsibility of the PostgreSQL CI job.
