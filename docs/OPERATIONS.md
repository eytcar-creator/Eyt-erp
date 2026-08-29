# E.Y.T ERP Operations

## Production checks

The API exposes two probes:

- `GET /health` confirms the application process is responding.
- `GET /ready` confirms the application can connect to PostgreSQL and execute `SELECT 1`.

A deployment should only receive traffic after `/ready` returns HTTP 200.

## Runtime

The production container starts:

`uvicorn api.production.main:app --host 0.0.0.0 --port 8000`

Required environment variable:

`DATABASE_URL`

## Operational flow

Product Master -> Procurement -> Receiving -> Inventory -> Reservation -> Production/BOM -> Costing -> Sales -> Finance -> Dashboard

Inventory mutations must use the inventory APIs so on-hand and reserved quantities remain consistent. Production and sales integrations should reference product codes and warehouse codes rather than maintaining parallel stock ledgers.

## Security

Keep production secrets outside the repository. `.env.example` is documentation only. JWT/RBAC permissions remain enforced at the API boundary.
