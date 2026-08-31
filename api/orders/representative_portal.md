# E.Y.T Representative Portal

## MVP screens

### Dashboard
- Today's orders
- Pending confirmation
- Available credit
- Outstanding balance
- Open shipments
- Monthly sales

### New Order
1. Select customer.
2. Select warehouse.
3. Search product/SKU/barcode.
4. Enter quantity.
5. Show representative price and discount.
6. Show available stock.
7. Submit order.
8. Display `EYT-ORD-YYYY-XXXXXX`.

### Order Tracking
Filter by order number, customer, date and status.

### Account
Show credit limit, used credit, outstanding balance, payment history and price tier.

## Rules
- Representative sees only authorized customers and territory.
- Price overrides require a separate permission.
- Stock shown is available-to-promise, not raw physical stock.
- Order confirmation must pass credit and inventory checks.
- Every action is audit logged.
