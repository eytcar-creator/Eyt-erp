# E.Y.T Unified Order Management

## Scope
Single order center for retail customers, mechanics, shops, wholesalers, representatives and sales staff.

## Channels
WEBSITE, WHATSAPP, PHONE, INSTAGRAM, SHOP, REPRESENTATIVE, SALES_STAFF.

## Flow
`Channel -> Order -> Customer validation -> Price list -> Inventory check -> Reservation -> Payment/Credit -> Fulfillment -> QC -> Shipment -> Delivery -> CRM follow-up`

## Order identity
Orders keep the existing `sales_orders.order_no` as the business identifier. Recommended format: `EYT-ORD-YYYY-XXXXXX`.

## Customer pricing
Supported price levels: RETAIL, MECHANIC, WHOLESALE, REPRESENTATIVE, VIP. A representative can have an assigned price list and credit limit.

## Representative model
Each representative has a unique code, territory, optional linked customer account, price level, credit limit and credit balance.

## Inventory reservation
`inventory_reservations` records product, warehouse, quantity and lifecycle state: RESERVED, RELEASED, FULFILLED.

## Implementation notes
- Migration 009 is idempotent and extends migration 006 rather than replacing it.
- Existing production and sales schemas remain intact.
- Future API endpoints should expose order intake, pricing preview, confirmation, reservation, fulfillment and representative portal operations.
- n8n can consume the order events later for WhatsApp/site/CRM automation.
