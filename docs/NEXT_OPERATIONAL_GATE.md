# E.Y.T ERP — Next Operational Gate

## Objective
Move from contract-complete MVP modules to a single executable end-to-end operational flow on the existing ERP architecture.

## Canonical flow
Master Catalog → Procurement/Receiving → Inventory → BOM → Production → QC → Finished Goods → Sales → Receivables → Dashboard

## Acceptance
- One canonical Product UUID is used throughout the flow.
- Inventory movements are ledger-backed and auditable.
- BOM consumption is deterministic.
- Production operations retain route, contractor/service, transport and material holding timestamps where applicable.
- QC release is required before finished goods become sellable.
- Sales and receivables preserve the same product and transaction identities.
- No second product master or parallel ERP architecture is introduced.
- Existing CI gates remain green.

## Execution rule
The next implementation must close the largest remaining gap between the documented operational contracts and a runnable end-to-end business transaction. Prefer executable API/database integration and tests over additional documentation-only work.
