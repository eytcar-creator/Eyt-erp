# EYT Core Master Schema v1.0

Migration: `023_eyt_core_master_v1.sql`

## Canonical master entities

- `eyt_product_master`: Product UUID, SKU, Code128, pricing and cost snapshots.
- `eyt_vehicle_master`: make/model/generation/trim/year/engine/transmission.
- `eyt_product_vehicle_fitment`: product-to-vehicle compatibility and OE references.
- `eyt_customer_master`: end customers, stores, mechanics, representatives and other customer types.
- `eyt_supplier_master`: suppliers and contractors.
- `eyt_warehouse_master`: warehouses and stock locations.
- `eyt_customer_vehicle`: vehicles owned/serviced by customers.
- `eyt_product_alias`: OEM/market aliases and cross-reference codes.

## Integration rule

The UUID in the master tables is the canonical identity. Existing legacy IDs and product-code/product-name fields are retained during migration.

New order/production records should populate:

- `sales_order_items.product_master_id`
- `sales_orders.customer_master_id`
- `production_orders.product_master_id`
- `production_orders.customer_master_id`

No hard deletion or destructive conversion is performed by this migration.

## Next migration

The next step is BOM + routing + cost linkage:

`Product Master -> BOM -> Routing -> Material Consumption -> Production Cost -> QC -> Inventory -> Sales -> Invoice -> Collection -> Cash Profit`
