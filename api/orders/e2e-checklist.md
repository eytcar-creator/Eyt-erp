# E.Y.T Order Center — Completion Gate

## Automated checks
- [x] Order payload validation
- [x] Empty-order rejection
- [x] Positive quantity validation
- [x] Atomic stock reservation design
- [x] Order lifecycle rules
- [x] Audit requirement
- [x] Post-commit automation event contract

## Deployment checks
- [ ] Configure PostgreSQL connection/pool from the production environment
- [ ] Apply order migrations
- [ ] Register `api.v1.orders` router in the actual FastAPI application entrypoint
- [ ] Configure authentication/RBAC for representative and sales roles
- [ ] Connect real customer/product lookup endpoints
- [ ] Connect n8n webhook endpoint and secret through environment variables
- [ ] Run integration tests against a disposable PostgreSQL database
- [ ] Run smoke test: create → confirm → reserve → event

## Acceptance criteria
1. A representative can create an order only for an authorized customer.
2. The order cannot reserve more than available stock.
3. Confirmation and reservation either both commit or both roll back.
4. Duplicate external submissions do not create duplicate orders.
5. Every lifecycle transition is auditable.
6. Automation fires only after successful commit.
