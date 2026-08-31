# E.Y.T Order Center — Implementation Contract

## Purpose
Single operational entry point for orders from customers, representatives and all sales channels.

## Endpoints
- `POST /api/v1/orders` — create order and validate master data.
- `GET /api/v1/orders/{orderNo}` — retrieve order and lifecycle status.
- `POST /api/v1/orders/{orderNo}/confirm` — validate credit and stock, then reserve inventory atomically.

## Lifecycle
`DRAFT → PENDING_CONFIRMATION → CONFIRMED → RESERVED → PREPARING → READY_TO_SHIP → SHIPPED → DELIVERED`

Terminal states: `CANCELLED`, `RETURNED`.

## Channels
`WEBSITE`, `WHATSAPP`, `PHONE`, `INSTAGRAM`, `SHOP`, `REPRESENTATIVE`, `OTHER`.

## Confirmation rules
1. Customer must be active.
2. Representative, when supplied, must be active and authorized for the customer/territory.
3. Product must be active.
4. Quantity must be positive.
5. Effective price comes from the customer's price tier unless an authorized override exists.
6. Available stock is checked before reservation.
7. Credit exposure is checked against the customer's credit limit before confirmation when the order is not fully prepaid.
8. Reservation and order status change must occur in one database transaction.
9. Every status change must be auditable.

## Integration boundaries
- Inventory: availability and reservation.
- Sales/receivables: invoice, prepayment and balance.
- Production: shortage creates a supply/production signal; it does not silently oversell.
- CRM: customer history and follow-up events.
- Automation: outbound notifications/events can be consumed by n8n.

## Idempotency
Order creation integrations should provide an idempotency key. Repeated delivery of the same external request must not create duplicate orders.

## Security
Use existing E.Y.T authentication/RBAC. Order creation, price override, confirmation, fulfillment and cancellation are separate permissions. Never store API tokens or customer secrets in source control.
