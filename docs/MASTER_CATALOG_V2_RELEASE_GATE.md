# Master Catalog v2 Release Gate

## Required before merge

- [x] Product UUID remains stable and canonical
- [x] SKU and product code are unique identifiers
- [x] Vehicle fitment is modeled separately from product identity
- [x] E.Y.T category rules are explicit
- [x] سه‌شاخ is excluded from the catalog
- [x] Kit/Pack component relationships are defined
- [x] OEM and market aliases map to canonical products
- [x] Inventory and BOM are required to reference canonical product identity
- [x] Import/export remains based on stable external identifiers

## CI gate

All repository CI and integration checks must pass before merge.

## Operational acceptance

A product created through Master Catalog must be usable by procurement, receiving, inventory, BOM, production, QC and sales without creating a second product identity.
