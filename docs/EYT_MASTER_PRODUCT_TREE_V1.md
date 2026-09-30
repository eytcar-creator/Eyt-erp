# EYT Master Product Tree v1.0

## Canonical hierarchy

Vehicle Make -> Model -> Generation -> System -> Product Family -> Subfamily -> Physical Part -> EYT SKU -> Vehicle Application/OEM Cross Reference

### Product families

| Code | Family | Scope |
|---|---|---|
| STEERING | فرمان و جلوبندی فرمان | Core |
| FRONT_SUSPENSION | جلوبندی | Core |
| BUSHINGS | بوش‌ها | Core |
| MOUNTING | دسته‌موتور و متعلقات نصب | Core |
| BELLOWS_RUBBER | گردگیر و قطعات لاستیکی | Core |
| CONTROL_ARM | طبق و متعلقات طبق | Core |
| REPAIR_KITS | کیت‌های تعمیراتی | Core |
| TRADING | بازرگانی | Trading |

## Identity rules

- Physical Part is the reusable physical/manufacturing identity.
- EYT SKU is the commercial/inventory identity.
- Vehicle Application describes where the SKU fits.
- OEM/Cross Reference is an alias/reference, not a new physical part.
- One physical part may serve multiple vehicle applications.
- Do not create duplicate SKUs merely because the same physical part fits several vehicles.

## Capacity rules

| Family | Annual Minimum | Normal Annual Maximum | Rule |
|---|---:|---:|---|
| Front Suspension | 80,000 | 120,000 | Minimum mandatory; above max allowed with confirmed customer order override |
| Bushings | 40,000 | 80,000 | Minimum mandatory; above max allowed with confirmed customer order override |
| Bellows & Rubber / Slotted Rubber scope | 10,000 | 50,000 | Minimum mandatory; above max allowed with confirmed customer order override |
| Mounting | 5,000 | 20,000 | Minimum mandatory; above max allowed with confirmed customer order override |

These numbers are family-level planning policies. They must not be arbitrarily split across individual SKUs until demand/order evidence exists.

## ERP behavior

1. Annual plan below mandatory minimum -> alert/block planning approval.
2. Annual plan within minimum-to-normal-maximum -> normal capacity.
3. Annual plan above normal maximum with confirmed customer order -> CUSTOMER_ORDER_OVERRIDE.
4. Annual plan above normal maximum without confirmed customer order -> ABOVE_NORMAL_CAPACITY_REVIEW.
5. Normal maximum is not a sales ceiling.

## Data fields

family_id, subfamily_id, physical_part_id, sku, code128, product_type, procurement_mode, BOM, routing, annual_min_qty, annual_normal_max_qty, min_stock, reorder_point, max_stock, vehicle_fitments, OEM aliases, kit membership.
