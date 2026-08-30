# E.Y.T ERP — Sales Operational V2

## Scope
Operational sales flow from customer quotation through order approval and downstream fulfillment/accounting handoff.

## Flow
Customer → Quotation → Price/Discount → Approval → Sales Order → Inventory Reservation → Delivery Handoff → Invoice Handoff → Receivable Handoff.

## Invariants
- Sales order quantities must be positive.
- Discounts require an authorized policy/permission.
- Approved orders must retain price and approval traceability.
- Inventory reservation cannot exceed available/reservable stock.
- Delivery and invoice handoffs must reference the originating sales order.
- Sales mutations require appropriate sales permission.
- Sales mutations create auditable records.

## Pricing
Final line value = quantity × approved unit price − approved discount.
Order totals must reconcile with their line items.

## Release gate
Sales is complete for this phase only when required executable tests and ERP/Identity CI checks are green.