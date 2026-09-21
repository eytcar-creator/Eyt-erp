# E.Y.T ERP — Purchase & Receiving v1

## Scope

Purchase requests/orders and receiving are the next operational layer after Product Master and Inventory.

## Core invariants

1. Every purchase line references a Product Master UUID.
2. A purchase order does not increase stock.
3. A receiving transaction increases stock only after successful receipt confirmation.
4. Received quantity cannot exceed the ordered quantity unless an explicit over-receipt policy is enabled.
5. Every receipt creates an inventory transaction with warehouse, quantity, unit cost and source document.
6. Purchase and receiving mutations require authenticated principals and are audited.
7. Partial receipts are supported.
8. Purchase order status progresses through `draft -> approved -> partially_received -> received`.
9. A cancelled purchase order cannot be received.
10. Monetary values use deterministic decimal/monetary rounding.

## Suggested API contract

- `POST /api/purchase/requests`
- `POST /api/purchase/orders`
- `GET /api/purchase/orders/{order_no}`
- `POST /api/purchase/orders/{order_no}/approve`
- `POST /api/purchase/orders/{order_no}/receive`
- `GET /api/purchase/orders/{order_no}/receipts`

## Receiving payload

A receipt identifies the purchase order, warehouse and one or more product lines. Each line contains the Product Master UUID and received quantity. Unit cost is copied from the purchase line unless an authorized adjustment is supplied.

## E2E acceptance flow

Supplier -> Purchase Order -> Approval -> Partial/Full Receipt -> Inventory increase -> Audit -> Remaining quantity calculation -> Final receipt -> `received` status.

Synthetic CI data only; production secrets and customer data must never enter the tests.
