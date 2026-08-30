# E.Y.T ERP — BOM Operational V2 Contract

## 1. Scope
Define the canonical Bill of Materials contract between Master Catalog, Production Order, Inventory consumption, QC, Finished Goods and Costing.

## 2. Canonical identity
Every BOM header and component must reference an existing canonical Product UUID from Master Catalog v2. Free-text product names are not valid BOM identities.

A BOM header represents the product being produced, while each BOM line represents one required or optional component product.

## 3. BOM header
Each BOM version contains:
- stable BOM UUID
- parent Product UUID
- version number
- status: draft / active / retired
- effective-from and optional effective-to dates
- yield quantity and unit of measure
- revision reason
- created/approved metadata

Only one active BOM version may govern a parent product for a given effective period.

## 4. BOM lines
Each component line contains:
- component Product UUID
- quantity per parent yield
- unit of measure
- scrap/waste allowance where applicable
- required/optional flag
- sequence/operation reference where required
- source/reference notes

Component quantities must be positive. A BOM cannot reference itself directly or through a circular dependency.

## 5. Master Catalog invariants
- Product UUID is immutable.
- SKU/product code uniqueness remains owned by Master Catalog.
- Fitment belongs to the product/application model, not the BOM identity.
- Kit/Pack relationships must reference canonical products.
- The prohibited category `سه‌شاخ` remains excluded.

## 6. Versioning and change control
BOM changes create a new revision/version rather than mutating historical production records. Historical production orders retain the BOM version used at release time.

Activating a new BOM requires validation that all referenced products exist and are active/usable for production.

## 7. Production integration
Production Order release resolves the active BOM version into a frozen production snapshot. Material requirements are calculated from the released BOM and production quantity.

Inventory consumption must reference Product UUID and the production order/BOM version. BOM changes after production release must not rewrite historical requirements.

## 8. Costing integration
BOM material requirements feed production costing. Material cost is calculated from actual inventory consumption where available, with planned BOM quantities retained for variance analysis.

Scrap and waste must remain distinguishable from normal component quantity.

## 9. Kit / Pack support
A sellable Kit/Pack may use BOM-style component relationships while preserving individual component product identity and the ability to sell approved components separately.

## 10. Permissions and auditability
BOM creation, revision, approval, activation and retirement are controlled operations and must be auditable. Production release requires an active approved BOM.

## 11. Import / export
BOM import/export must use stable Product UUIDs and BOM UUID/version identifiers. External SKU/OEM/reference values are mappings, not replacements for canonical identity.

## 12. Acceptance criteria
BOM v2 is accepted when:
- canonical Product UUID references are enforced
- BOM versions are immutable after production release
- circular dependencies are rejected
- only valid products can be components
- active BOM selection is deterministic
- production material requirements can be generated from the released BOM
- inventory consumption preserves Product UUID and BOM version
- costing can reconcile planned versus actual material usage
- audit records exist for BOM lifecycle mutations
- PostgreSQL E2E and ERP/Identity CI gates are green
