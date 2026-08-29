# E.Y.T Product Master + Inventory v1

## Product Master

The operational master record is `products` and uses a UUID primary key plus unique `sku` and `product_code` identifiers.

Core fields include:
- Persian/English names
- category and product type
- E.Y.T brand
- unit and barcode
- OEM code and specification
- weight
- purchase/sale prices
- minimum, maximum and reorder stock levels
- vehicle fitment by make/model/trim/year range

Vehicle fitments and market aliases are stored separately so one part can serve multiple vehicle applications without duplicating the master record.

## E.Y.T category rules

The seed hierarchy includes suspension, steering ball joint, control-arm ball joint, bush, stabilizer, engine mount, raw material and production service.

`سه‌شاخ` is intentionally not part of the master category seed.

## Inventory

Inventory is ledger-based. Every movement is recorded in `inventory_transactions`; reservations are recorded separately in `inventory_reservations`.

Positive movements: receipt, transfer-in, return, production receipt and adjustment.

Negative movements: issue, transfer-out, consumption and scrap.

Available stock is calculated as on-hand minus active reservations. Transaction creation uses a PostgreSQL advisory lock per product/warehouse pair to prevent concurrent overselling.

## Warehouses

The initial operational seed contains:
- MAIN: Main Warehouse
- TABRIZ-ASSEMBLY: Tabriz Assembly
- TABRIZ-WORKSHOP-2: Tabriz Workshop 2
- TEHRAN-SHOP: Tehran Shop

## API

- `POST /api/products`
- `GET /api/products`
- `GET /api/products/{product_code}`
- `POST /api/products/{product_code}/fitments`
- `GET /api/inventory/balance/{product_code}/{warehouse_code}`
- `POST /api/inventory/transactions`
- `POST /api/inventory/reservations`
- `POST /api/inventory/reservations/{reservation_id}/release`

All write/read endpoints are protected by RBAC and product/inventory actions are auditable where they mutate master data.
