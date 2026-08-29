# E.Y.T ERP Production Domain

## Domain entities

- ProductionOrder
- MaterialLot
- ProductionOperation
- Contractor
- QualityInspection
- ProductionCost
- CustomerPrepayment
- Collection
- CapitalHoldingCost
- ProductionTraceability
- ProductionAlert

## Production operation state machine

`pending -> dispatched -> in_progress -> qc_pending -> completed`

Exceptional states:

`blocked`, `rejected`, `cancelled`

## Reference route

`CUT -> FORGE -> DRILL -> CNC -> TAP -> BLACK_PLATE -> FINAL_QC`

The domain must preserve the actual sequence, quantities and timestamps. Financial records are linked to the production order and operation rather than stored as untraceable totals.

## Costing principle

True cost is assembled from material, subcontracting, labor, transport, overhead, QC, scrap and capital holding cost. Customer prepayments are considered when calculating the capital actually tied up by E.Y.T.
