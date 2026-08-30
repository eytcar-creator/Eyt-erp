# Production Execution V2 Release Gate

## Required before merge
- [x] Production release resolves an approved active BOM
- [x] Product UUID/SKU/product_code identity remains canonical
- [x] Released production freezes BOM version and material requirements
- [x] Planned material consumption is calculated from BOM yield
- [x] Actual inventory consumption preserves Product UUID and production-order traceability
- [x] Scrap/waste is separated from normal material consumption
- [x] Operation quantity reconciliation is enforced
- [x] Contractor/service operations require accountable ownership
- [x] Material sleep/holding timestamps are preserved
- [x] QC blocks normal finished-goods release on failure
- [x] Actual execution costs feed costing and variance analysis
- [x] Production mutations are permission-controlled and audited

## E.Y.T route coverage
The gate must support cutting, forging, drilling, CNC, threading/tapping, black plating, assembly and final QC without hard-coding one vehicle or product.

## CI gate
PostgreSQL integration/E2E, E.Y.T ERP CI and Identity/RBAC CI must pass before merge.

## Operational acceptance
One synthetic production order must be traceable from canonical Product + approved BOM through material issue, every operation/contractor step, QC, finished-goods receipt, costing and audit without creating a duplicate product identity.
