# E.Y.T ERP | API Test Strategy

## Scope

This phase establishes the executable-test target for the integration API. Tests should run in CI against an isolated PostgreSQL database and must not touch production data.

## Required test groups

### Health
- `GET /api/v1/health` returns HTTP 200.

### Catalog
- Product search returns only active products.
- Vehicle fitment filters return confirmed fitments when requested.
- OEM/cross-reference lookup returns the correct product.

### B2B orders
- Authenticated customer can create an order request for its own account.
- Unauthenticated requests return 401.
- Customer cannot submit an order for another customer.
- Quantity must be positive.
- Unknown product returns a validation error.
- Duplicate `external_reference` is rejected/idempotent.
- Client-supplied price cannot override server-side price resolution.

### Inventory
- Availability respects warehouse authorization.
- Reserved quantity is not reported as freely available.

### Authorization
- Every protected endpoint is default-deny.
- Role permissions are enforced.
- Approval limits and risk policies are enforced.
- Sensitive actions create an audit record.

### Webhooks
- Valid event is accepted with HTTP 202.
- Invalid envelope is rejected.
- Duplicate `event_id` is safely ignored/rejected.
- Correlation ID is retained through downstream processing.

## CI gates

1. Database migration test.
2. Unit tests.
3. API integration tests.
4. Authorization/security tests.
5. Lint/format checks.
6. No secrets in repository.

## Definition of done

No API endpoint is considered production-ready until authentication, authorization, validation, idempotency, auditability and automated tests are present for its critical paths.
