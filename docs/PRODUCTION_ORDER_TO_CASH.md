# E.Y.T ERP — Production Order to Cash

## Scope
The operational core connects demand, planning, procurement, production, subcontractors, quality control, inventory, sales, customer prepayments, collections, and true production cost.

## Reference production order
- Production order: `MO-ARIO-0001`
- Product: Ario tie-rod-end body
- Target quantity: 2,000 pcs
- Raw material: CK45 steel, diameter 24 mm

## Production route
1. Material purchase and receiving
2. Cutting
3. Forging
4. Drilling
5. CNC machining
6. Threading / tapping
7. Black plating
8. Final quality control
9. Finished-goods inventory

## Traceability
Every operation records the production order, item/batch, responsible person or contractor, start/end dates, input quantity, accepted quantity, rejected quantity, waste reason, operation cost, transport cost, QC result, and technical documents.

## True production cost
True cost includes material, subcontracting, labor, transport, overhead, QC, scrap, and capital holding cost.

Customer prepayments are recorded against the order and reduce the capital actually invested by E.Y.T when calculating capital holding cost.

## Lifecycle dates
Order date -> planned start -> actual start -> operation start/end dates -> warehouse receipt -> sale -> collection due date -> actual collection.

## Alerts
- material shortage
- contractor delay
- overdue operation
- abnormal waste
- QC rejection
- inventory shortage
- supplier payment due
- customer receivable due
- delivery risk
