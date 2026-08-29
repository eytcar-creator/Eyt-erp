# E.Y.T ERP API

Production FastAPI backend for the E.Y.T auto-parts ERP.

## Runtime

The production application is exposed from `api.production.main:app` and combines the authentication/RBAC, production, costing, dashboard, sales, procurement, finance, commercial, and inventory-flow routers.

## System endpoints

- `GET /health` - liveness check
- `GET /ready` - PostgreSQL readiness check
- `GET /docs` - interactive OpenAPI documentation

## Authentication

Authentication uses short-lived JWT access tokens plus rotating refresh tokens. Protected routes resolve permissions through the E.Y.T role/permission model and audit important mutations.

Required environment variables:

- `DATABASE_URL`
- `JWT_SECRET`
- `BOOTSTRAP_SECRET`

Optional token settings:

- `ACCESS_TOKEN_MINUTES` (default `15`)
- `REFRESH_TOKEN_DAYS` (default `30`)

## Modules

- Authentication and RBAC
- Product master and inventory
- Production and work orders
- Quality control
- Procurement and suppliers
- Sales and commercial operations
- Finance and receivables/payables
- Costing
- Dashboard and reporting
- Inventory flow and stock movements

## Local run

```bash
pip install -r requirements.txt
uvicorn api.production.main:app --reload
```

## Tests

```bash
pytest -q
```

© E.Y.T
