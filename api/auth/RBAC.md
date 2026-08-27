# E.Y.T ERP | Authentication & RBAC

## Roles

### Internal
- CEO
- General Manager
- Sales Manager
- Procurement Manager
- Production Manager
- QC Manager
- Warehouse Manager
- Finance Manager
- Accountant
- Sales Agent
- Warehouse Operator
- Production Operator
- Read Only

### External
- B2B Customer Admin
- B2B Customer Buyer
- B2B Customer Finance

## Authorization model

Authentication identifies the user. RBAC determines what the user may do. Entity-level authorization then restricts records to the company, warehouse, customer or scope assigned to that user.

## Rules

1. Default deny for every protected endpoint.
2. Permissions are granted through roles, never hard-coded per user.
3. External customers can access only their own customer record and authorized child records.
4. Customer-specific prices, credit limits and financial balances are resolved server-side.
5. Approval permissions must respect amount and risk policies from the approval engine.
6. Sensitive actions require audit logging with actor, entity, timestamp and correlation ID.
7. Tokens must have expiry and rotation/revocation support.
8. Passwords are stored only as strong salted hashes; never in plaintext.
9. Secrets and signing keys belong in environment/secret storage, never Git.
10. Service-to-service calls use scoped credentials and least privilege.

## Suggested permission namespaces

- `catalog.read`
- `inventory.read`
- `inventory.adjust`
- `sales.quote.create`
- `sales.order.create`
- `sales.order.approve`
- `sales.discount.override`
- `delivery.create`
- `invoice.read`
- `finance.receipt.create`
- `finance.payment.approve`
- `production.read`
- `production.execute`
- `qc.inspect`
- `qc.release`
- `purchasing.create`
- `purchasing.approve`
- `reporting.read`
- `admin.users.manage`
- `admin.roles.manage`

## Authentication lifecycle

Login -> credential verification -> short-lived access token -> authorized API request -> audit event -> token refresh/revocation as required.

## B2B customer isolation

Every customer-facing request must derive `customer_id` from the authenticated principal/session and compare it with the requested resource scope. A client-supplied customer ID is never authoritative.

## Next implementation

Implement the identity provider/auth service, user-role assignments, refresh-token strategy, endpoint middleware, customer tenancy checks and automated authorization tests before exposing the portal publicly.
