# E.Y.T Order Center — Completion Gate

## Automated checks
- [x] Order payload validation
- [x] Empty-order rejection
- [x] Positive quantity validation
- [x] Duplicate product lines rejected before persistence
- [x] Client-supplied prices ignored; prices resolved server-side
- [x] Website customer ID bound to authenticated customer session
- [x] Internal order create/read/confirm routes require the trusted channel token
- [x] Explicit zero/invalid configured prices are rejected without permissive fallback
- [x] Order subtotal, total amount, and line totals persisted at creation
- [x] Atomic stock reservation design
- [x] Order lifecycle rules
- [x] Audit requirement
- [x] Post-commit automation event contract
- [x] CI workflows: ERP CI, Identity/RBAC, Production Validation, PostgreSQL Integration, Backend Hardening

## Deployment checks
- [x] Register Order Center router and configure repository/gateway in the FastAPI application entrypoint (verified in `api/production/main.py`)
- [ ] Configure production `DATABASE_URL`, `JWT_SECRET`, and `EYT_ERP_CHANNEL_TOKEN` using actual secret values
- [ ] Apply the full migration chain to the target production database and verify schema version
- [ ] Verify the production customer/product/price data is consistent across legacy and master-data tables
- [ ] Configure trusted server-side integrations; never expose `EYT_ERP_CHANNEL_TOKEN` to browser/mobile clients
- [ ] Configure n8n webhook URL and secrets in the deployed environment
- [ ] Run the smoke test against the target environment: create → confirm → reserve → event
- [ ] Verify invoice, payment/receivable, delivery and actual-cost reconciliation against real records
- [ ] Confirm backup, restore and rollback procedure before go-live

## Acceptance criteria
1. A customer can create a website order only for their own authenticated customer account.
2. Internal channel orders and their reads/confirmation require a trusted server-side credential.
3. The order cannot reserve more than available stock.
4. Confirmation and reservation either both commit or both roll back.
5. Duplicate external submissions do not create duplicate orders.
6. The persisted order header and line totals reconcile exactly.
7. Every lifecycle transition is auditable.
8. Automation fires only after successful commit.
9. A real order can be traced from order through stock, invoice, delivery and realized margin without manual duplicate entry.
