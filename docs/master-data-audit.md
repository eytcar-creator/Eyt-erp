# E.Y.T ERP Master Data Repository Audit
Date: 2026-10-20
Status: Initial code-level audit; runtime database and CI results not verified.

## Scope checked
- `README.md`
- `docs/system-map.md`
- `database/migrations/004_product_master_inventory.sql`
- `database/migrations/010_eyt_master_data.sql`
- `database/migrations/029_eyt_core_master_v1.sql`
- `database/migrations/030_eyt_bom_routing_cost_engine_v1.sql`
- `database/migrations/README.md`
- `api/production/README.md` and `api/production/openapi.yaml`
- `docker-compose.production.yml`
- Open PR #81 and its stated dependency on PR #80.

## Findings

### Existing capabilities: do not recreate these
1. Migration 004 already defines legacy `products`, `product_categories`, `product_vehicle_fitments`, `product_aliases`, `warehouses`, inventory transactions, and reservations.
2. Migration 010 already defines `vehicle_master`, `product_vehicle_compatibility`, `kit_bom_master`, and `price_master`.
3. Migration 029 adds a newer UUID-oriented master layer: `eyt_product_master`, `eyt_vehicle_master`, `eyt_product_vehicle_fitment`, `eyt_customer_master`, `eyt_supplier_master`, `eyt_warehouse_master`, `eyt_customer_vehicle`, and `eyt_product_alias`. It adds bridge columns to legacy sales and production tables.
4. Migration 030 adds versioned `eyt_bom`, `eyt_bom_item`, `eyt_routing`, `eyt_routing_operation`, cost snapshots, and cost views/functions.
5. The repository README describes a FastAPI/PostgreSQL ERP and production deployment via Docker Compose. The production API contract already documents production order, operation, QC, cost, prepayment, and collection endpoints.
6. PR #81 is open and describes a read-only commercial gate with PASS / NEED_PRODUCTION / BLOCK outcomes. It explicitly says final reservation and confirmation remain in the existing atomic Order Center path. Preserve this boundary.

## Main architectural risk
There are multiple overlapping generations of product and vehicle/fitment data:
- Legacy: `products` + `product_vehicle_fitments` (004)
- First expanded master: `vehicle_master` + `product_vehicle_compatibility` (010)
- New UUID master: `eyt_product_master` + `eyt_vehicle_master` + `eyt_product_vehicle_fitment` (029)

The repository also has parallel warehouse and price concepts. Adding another set of master tables now would worsen fragmentation. The code and migrations establish that these structures exist, but this audit has not yet proven which tables are populated in the live production database or which API paths are authoritative at runtime.

## Required next actions
1. **No new product/vehicle/fitment tables yet.**
2. Inspect migration runner and the complete migration chain, including compatibility assumptions, duplicate migration numbering in comments, and the later date-prefixed migrations.
3. Trace current API read/write paths and tests for product resolution, vehicle fitment, order confirmation, and inventory reservation.
4. Query the actual deployed database read-only (if authorized credentials/environment are available) to measure table row counts, null bridge IDs, duplicate SKU/code/barcode, unresolved fitments, and migration ledger state. Do not run migrations or mutate production data as part of this audit.
5. Select one canonical master model. Prefer extending the UUID `eyt_*` model only if code-path and data evidence confirms it is the intended authority; otherwise document the migration plan before changing schemas.
6. Add explicit legacy-to-canonical resolution/bridge tests, including duplicate, unknown SKU, ambiguous fitment, inactive product, and permission-denied cases.
7. Keep the PR #81 commercial gate read-only. Stock reservation must happen only through the existing atomic confirmation path.

## E.Y.T catalog constraints for future seed/import validation
- Ball-joint catalog entries are only `سیبک فرمان` and `سیبک طبق`.
- `سه‌شاخ` is not an E.Y.T catalog product.
- Keep `بلبرینگ سرکمک` distinct from `توپی سرکمک`; do not rename it `یاتاقان سرکمک`.
- Model front/rear stabilizer links and front/rear slotted rubber separately.
- Store small/large bushing, axle, side, vehicle generation/engine/transmission, and fitment approval explicitly where applicable.
- Heater/radiator hoses are hose products, not rings.

## Audit limitations
This is a repository-file review only. No test suite was executed, no production database was accessed, no deployment health was checked, and no production migration was run. PR #81 was observed as open at the time of review; its CI checks and merge status require a separate live check.
