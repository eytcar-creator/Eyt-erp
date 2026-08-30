# E.Y.T ERP — Costing Operational V2

## Scope
Operational product and production costing on the current main baseline.

## Cost model
Unit cost is derived from traceable cost components:

1. Direct material cost
2. Production operation cost
3. Contractor/service cost
4. Transport cost
5. QC loss and waste allocation
6. Other approved direct costs

## Core formula
`Total Cost = Materials + Operations + Contractor + Transport + QC Loss Allocation + Approved Direct Costs`

`Unit Cost = Total Cost / Accepted Quantity`

Rejected and waste quantities must not be treated as sellable finished quantity.

## Traceability
Every cost component must reference its source document or operational event where applicable:
- purchase/receiving
- production operation
- contractor
- transport
- QC disposition

## Invariants
- Cost amounts cannot be negative unless represented as an approved credit/adjustment.
- Accepted quantity used for unit costing must be greater than zero.
- Cost allocation must preserve total cost.
- QC rejected/waste quantities must remain visible in costing.
- Finalized cost records require auditability.
- Cost mutations require appropriate permission.

## Release gate
Costing is complete for this phase only when executable tests and required CI checks are green.
