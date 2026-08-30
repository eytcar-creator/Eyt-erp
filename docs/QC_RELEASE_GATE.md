# E.Y.T QC Operational V2 — Release Gate

## Required
- [x] Quality Batch has unique batch number and production/product references.
- [x] Inspection records inspector, result, quantities and timestamp.
- [x] Accepted + rejected quantities cannot exceed planned quantity.
- [x] Defect model supports severity and quantity.
- [x] Traceability records batch and optional serial number events.
- [x] Failed/blocked batches cannot be released.
- [x] Finished Goods Release is unique per quality batch.
- [x] Release is permission-protected and auditable.
- [x] QC API is mounted in the operational FastAPI application.
- [x] Contract tests cover input invariants.

## Acceptance
PostgreSQL migration chain, ERP CI, Identity/RBAC CI and integration/E2E checks must pass before merge.

## Operational outcome
A production batch cannot become saleable finished goods without an explicit QC pass and release event. Inventory and downstream sales must consume the released quantity, preserving batch traceability.
