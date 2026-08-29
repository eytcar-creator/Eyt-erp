# E.Y.T ERP operational scripts

## Smoke test

`operational_smoke_test.py` verifies that a deployed ERP instance is reachable and that both the application health and database readiness endpoints return HTTP 200.

Example:

```bash
BASE_URL=https://erp.example.com python scripts/operational_smoke_test.py
```

This is a deployment probe, not a substitute for authenticated business-flow tests. Real customer, supplier, financial, or authentication credentials must never be stored in Git.
