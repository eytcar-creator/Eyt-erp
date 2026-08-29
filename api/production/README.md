# E.Y.T ERP Production API

## Initial API contract

### Create production order
`POST /api/production/orders`

Creates a production order with product, target quantity, customer, order date and planned dates.

### Get production order
`GET /api/production/orders/{orderNo}`

Returns order status, operations, materials, costs, QC, prepayments, collections and alerts.

### Start operation
`POST /api/production/orders/{orderNo}/operations/{operationCode}/start`

Records actual start time and responsible contractor/person.

### Complete operation
`POST /api/production/orders/{orderNo}/operations/{operationCode}/complete`

Records actual end time, input quantity, accepted quantity, rejected quantity, waste, service cost and transport cost.

### Record QC
`POST /api/production/orders/{orderNo}/qc`

Records inspected, accepted and rejected quantities and the QC result.

### Record cost
`POST /api/production/orders/{orderNo}/costs`

Records material, subcontractor, labor, transport, overhead, QC, scrap and other production costs.

### Record customer prepayment
`POST /api/production/orders/{orderNo}/prepayments`

Links customer prepayments to the production order for working-capital and holding-cost calculations.

### Record collection
`POST /api/production/orders/{orderNo}/collections`

Records due date, collection date and amount received.

### Production dashboard
`GET /api/production/dashboard`

Returns open orders, overdue operations, shortages, QC failures, contractor balances, customer receivables and estimated true production cost.

## Business rules

- An operation cannot be completed without an actual start time.
- Accepted + rejected + waste must reconcile with the operation input quantity according to the configured production rules.
- Final QC must pass before finished quantity is released to finished-goods inventory.
- Customer prepayments reduce the capital base used for holding-cost calculation.
- Every subcontracting operation must have a contractor or responsible party.
- All production lifecycle dates must remain auditable.
