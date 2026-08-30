# Production Execution V2 Status

Status: integration gate prepared on top of BOM V2 and the existing Production V2 baseline.

## Current main baseline
- Master Catalog V2: merged
- BOM V2: merged
- Production V2 operational contract: already present
- PostgreSQL migration-chain gate: merged

## This gate
Production Execution V2 binds the BOM release snapshot to actual material consumption, operation/contractor execution, QC handoff, finished-goods receipt and true costing.

## E.Y.T-specific requirements
- CK45 / Ø24 reference material is represented by canonical product identity.
- Forging, drilling, CNC, threading/tapping, black plating and assembly can be tracked as ordered operations.
- Contractor and transport costs remain attached to the relevant operation.
- Material sleep time is measurable from receiving through production consumption/finished-goods completion.
- Historical production keeps the exact BOM revision and actual consumption used.

## Next gate
PostgreSQL E2E plus ERP CI and Identity/RBAC CI, then merge to `main`.
