# E.Y.T ERP — Sprint 3 Production Lifecycle

## Implemented

- Production operations now have an explicit `start` lifecycle.
- Completion is rejected unless an operation is already `in_progress`.
- Starting an operation moves the production order to `in_progress` and records the first actual start timestamp.
- Completion records accepted, rejected, waste, subcontractor/service cost and transport cost.
- URL operation code must match the payload operation code.
- Quantity reconciliation is enforced: accepted + rejected + waste = input.
- Negative production quantities are rejected.
- Operation lifecycle endpoints require `production.execute` permission.
- Automated tests cover quantity reconciliation and invalid quantities.

## API

`POST /api/production/orders/{orderNo}/operations/{operationCode}/start`

`POST /api/production/orders/{orderNo}/operations/{operationCode}/complete`

## Next operational layer

1. Product Master and SKU/UUID governance.
2. BOM and material reservation/shortage checks.
3. Raw-material issue and finished-goods receipt.
4. QC release gate before finished-goods inventory.
5. Cost ledger including material, subcontracting, labor, transport, overhead, QC, scrap and holding cost.
6. Purchasing, suppliers and contractor balances.
7. Sales orders, delivery, invoices, collections and receivables.
8. Management dashboard and n8n automation.
