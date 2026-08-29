# E.Y.T ERP — QC Operational V2

## Scope
Operational quality control contract for production and receiving flows.

## Flow
Receiving/Production → QC Inspection → Pass / Reject / Rework → Inventory disposition → Audit.

## Invariants
- Inspected quantity cannot be negative.
- Accepted + rejected + rework must equal inspected quantity.
- QC disposition must reference a valid source transaction/order.
- Rejected stock cannot silently enter available inventory.
- QC mutations require the appropriate QC permission.
- QC mutations create audit records.

## Release gate
QC is complete for this phase only when PostgreSQL E2E tests and ERP CI plus Identity/RBAC CI are green.
