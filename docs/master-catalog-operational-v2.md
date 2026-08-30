# E.Y.T Master Catalog — Operational v2 Contract

## 1. Purpose

Define the canonical product master and vehicle application model used by Inventory, BOM, Production, QC, Sales and Finance.

## 2. Canonical Product Identity

Each sellable or stockable item is one canonical product record with:

- stable Product UUID
- unique E.Y.T product code
- unique SKU
- Persian and English names
- product category and product type
- brand / manufacturer identity
- unit of measure
- barcode
- OEM/reference code set
- technical specification and notes
- weight where applicable
- purchasing and sales pricing references
- minimum, maximum and reorder levels
- active/inactive lifecycle state

Product UUID is immutable and must remain stable across price changes, packaging changes, inventory movements and vehicle-fitment updates.

## 3. Vehicle Fitment

Vehicle application is a separate relation from the product master. A product may fit multiple applications without creating duplicate product records.

Fitment supports:

- make
- model
- trim / grade
- production year range
- engine / drivetrain qualifier where required
- market alias
- fitment notes
- source/reference
- active state

## 4. Category Rules

The E.Y.T category tree must preserve these business rules:

- سیبک‌ها → سیبک فرمان / سیبک طبق
- بوش‌ها → خانواده جلوبندی / تعلیق
- سه‌شاخ → ممنوع در Category Tree و Master Catalog
- دسته موتور → خانواده جداگانه برای engine mounts
- مواد اولیه و خدمات تولیدی → non-sellable operational categories

A category is not a substitute for vehicle fitment or product identity.

## 5. Kit and Pack

Kits and packs are product structures, not duplicated master records.

Each kit/pack must preserve:

- parent product
- component product
- quantity
- required/optional flag
- packaging definition
- ability to sell component products individually

Example operational components may include ball joints, dust/bump-stop items, tie-rod ends, stabilizer links and other approved E.Y.T catalog items.

## 6. OEM and Market References

OEM numbers, supplier references and market aliases are many-to-one references to the canonical Product UUID. Reference changes must not create a new product unless the physical/functional item is materially different.

## 7. Data Invariants

1. Product UUID is immutable.
2. SKU and product code are unique.
3. An inactive product cannot receive a new normal sales order line.
4. Fitment must reference an existing product.
5. Kit components must reference existing products.
6. A prohibited category item such as سه‌شاخ must not be inserted into the catalog.
7. Inventory must reference canonical Product UUID, never free-text product names.
8. Historical transactions retain their original product identity.

## 8. Downstream Contract

The Master Catalog is the upstream identity source for:

`Master Catalog → Procurement → Receiving → Inventory → BOM → Production → QC → Finished Goods → Sales → Receivables → Dashboard`

Downstream modules must not create competing product identities.

## 9. Import / Export Readiness

The model must remain compatible with controlled import/export to Excel, Odoo and future integrations. External identifiers are references and must map back to the stable Product UUID.

## 10. Acceptance Gate

Master Catalog v2 is accepted only when:

- canonical product identity is unique and stable
- fitment is normalized
- category rules are enforced
- kits/packs preserve component relationships
- prohibited categories are rejected
- inventory/BOM references use canonical product identity
- CI and integration tests remain green
