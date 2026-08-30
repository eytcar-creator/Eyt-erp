# BOM v2 Release Gate

## Required before merge
- [x] BOM header references canonical parent Product UUID
- [x] BOM components reference canonical Product UUID
- [x] BOM version/revision lifecycle is explicit
- [x] Historical production retains the released BOM version
- [x] Circular BOM dependencies are prohibited
- [x] Component quantities are positive and unit-aware
- [x] Active BOM selection is deterministic
- [x] Production release freezes BOM requirements
- [x] Inventory consumption preserves Product UUID and BOM version
- [x] Planned versus actual material usage can feed costing variance
- [x] Kit/Pack relationships remain compatible with canonical products
- [x] `سه‌شاخ` remains excluded from E.Y.T catalog/category rules
- [x] BOM lifecycle mutations are permission-controlled and auditable

## CI gate
ERP CI, Identity/RBAC CI and PostgreSQL integration/E2E checks must pass before merge.

## Operational acceptance
A production order must be releasable from an approved BOM, generate deterministic material requirements, consume canonical inventory items, and preserve the exact BOM revision used for the historical production record.
