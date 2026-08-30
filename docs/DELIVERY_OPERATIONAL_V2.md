# E.Y.T ERP — Delivery Operational V2

## Scope
Operational fulfillment flow from an approved sales order through picking, packing, dispatch, delivery confirmation, and invoice handoff.

## Flow
Approved Sales Order → Inventory Reservation → Picking → Packing → Dispatch → Delivery → Delivery Confirmation → Invoice Handoff.

## Invariants
- Delivery quantities must be positive and traceable to the originating sales order.
- Picking cannot exceed reserved/available quantity.
- Packed quantity cannot exceed picked quantity.
- Dispatched quantity cannot exceed packed quantity.
- Delivered quantity cannot exceed dispatched quantity.
- Delivery confirmation must be auditable.
- Inventory movement must be tied to the delivery transaction.
- Invoice handoff must reference the originating sales order/delivery.
- Delivery mutations require appropriate permission.

## Exceptions
Short shipment, damage, return, and failed delivery must be explicitly recorded and must not silently alter stock or receivables.

## Release gate
Delivery is complete for this phase only when required executable tests and ERP/Identity CI checks are green.