# E.Y.T ERP → Odoo Import Map

The ERP remains the canonical operational source. Odoo is an integration target, not a second product master.

| E.Y.T field | Odoo target | Rule |
|---|---|---|
| Product UUID | `x_eyt_product_uuid` | Immutable external identity |
| SKU | `default_code` | Unique stock code |
| product_code | `x_eyt_product_code` | Unique E.Y.T code |
| Persian name | `name` | Canonical display name |
| English name | `x_eyt_name_en` | Optional localized name |
| barcode | `barcode` | Unique where present |
| category | `categ_id` | Must follow E.Y.T taxonomy |
| UOM | `uom_id` | Preserve unit semantics |
| vehicle fitment | `x_eyt_fitment_ids` | Separate from product identity |
| OEM/reference | `x_eyt_reference_ids` | Many-to-one aliases to Product UUID |
| kit/pack components | BOM / packaging relations | Never duplicate component products |

## Import rules
1. Match by Product UUID first.
2. If UUID is absent in an external legacy row, resolve by controlled SKU/product_code mapping.
3. Never create a second product when an existing canonical identity matches.
4. Reject prohibited category `سه‌شاخ`.
5. Preserve historical identifiers and source references.
6. Validate fitment separately from product identity.

## Export rules
Every exported product record must contain Product UUID, SKU and product_code so it can be reconciled back to E.Y.T.
