# E.Y.T ERP — Production Operational V2

## Scope
Operational production execution on the current `main` baseline.

## Flow
Production Order → Operation Start → Operation Completion → QC → Finished Goods → Costing → Audit.

## Invariants
- Quantities cannot be negative.
- accepted + rejected + waste must equal input quantity.
- An operation must be started before completion.
- Duplicate in-progress operations are rejected.
- Production mutations require `production.execute` permission.
- Production mutations create audit records.

## Current API
- `POST /api/production/orders/{order_no}/operations/{operation_code}/start`
- `POST /api/production/orders/{order_no}/operations/{operation_code}/complete`

## Completion cost inputs
- service cost
- transport cost
- contractor

## Release gate
Production is considered complete for this phase only when PostgreSQL E2E tests and both ERP CI and Identity/RBAC CI are green.
