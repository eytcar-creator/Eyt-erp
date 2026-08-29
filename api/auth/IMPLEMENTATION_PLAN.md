# E.Y.T ERP | Identity & RBAC Sprint 2

## Scope
Implement the existing RBAC contract without changing the domain model already documented in `api/auth/RBAC.md`.

## Deliverables
1. User identity model and credential verification.
2. Role and permission assignments.
3. Short-lived access tokens.
4. Refresh-token rotation and revocation.
5. Protected-endpoint middleware with default deny.
6. Entity/customer scope enforcement.
7. Audit events for sensitive actions.
8. Automated authorization tests.

## Security rules
- Never store plaintext passwords.
- Never trust client-supplied `customer_id` for authorization.
- Keep signing keys and secrets outside Git.
- Apply least privilege and default deny.
- Keep authentication separate from authorization.

## Definition of done
- Authentication flow is covered by tests.
- Unauthorized requests return 401/403 consistently.
- Role permissions are enforced server-side.
- Customer isolation is tested.
- Token rotation/revocation is tested.
- Sensitive actions produce audit events.
- CI passes before the PR is merged.
