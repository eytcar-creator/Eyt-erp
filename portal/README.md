# E.Y.T B2B Customer Portal

## Purpose
A customer-facing portal consuming the unified `/api/v1` gateway. The portal must never implement separate pricing, inventory or order logic; ERP remains the source of truth.

## Customer journey

1. Authenticate customer account.
2. Search by vehicle, product name, SKU or OEM number.
3. View confirmed vehicle fitment and product details.
4. View customer-specific price list and quantity breaks.
5. Check available stock by permitted warehouse.
6. Build cart and submit B2B order request.
7. Track approval, reservation, delivery and invoice status.
8. View outstanding balance and receivable aging.
9. Download/order documents where authorized.

## Dashboard

- Open orders
- Orders awaiting approval
- Reserved stock
- Recent deliveries
- Open invoices
- Outstanding balance
- Overdue balance
- Active alerts/messages

## Security rules

- Customer sees only its own account, prices, orders, invoices and financial data.
- Customer-specific pricing is resolved server-side.
- Inventory quantities exposed according to authorization policy.
- Never trust client-submitted price, discount, customer ID or approval status.
- All order submissions use an idempotency/external reference.
- Sensitive actions require authenticated, authorized API requests.

## API dependencies

- `GET /catalog/products`
- `GET /catalog/fitments`
- `GET /inventory/availability`
- `POST /b2b/orders`
- `GET /webhooks/events` is not a customer endpoint and must remain internal.

## Phase 2

- Customer-specific credit status
- Order history and reorder
- Warranty registration
- QR-based installation/warranty confirmation
- Sales representative chat handoff
- Mobile-first PWA
