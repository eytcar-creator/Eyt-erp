# E.Y.T ERP — Production Execution V2 Integration Contract

## 1. Purpose

Bind the approved BOM V2 to the existing Production V2 execution flow so a production order can be released from one canonical product identity, consume the exact planned components, execute operations, record subcontracting, pass QC, receive finished goods and feed true costing without creating a second product identity.

## 2. Release lifecycle

`Draft → Planned → Released → In Production → QC Hold/Passed → Finished Goods → Closed`

A production order may enter `Released` only when:
- the parent Product UUID exists and is active;
- an approved active BOM version exists for the effective production date;
- every BOM component is a valid canonical Product UUID;
- required material availability/reservation checks pass or an explicit shortage exception is recorded;
- the operation route is complete and ordered.

## 3. Frozen production snapshot

At release time the system freezes:
- Product UUID and SKU/product_code;
- BOM UUID and version;
- BOM yield quantity and unit;
- each component Product UUID;
- planned quantity per component;
- approved scrap/waste allowance;
- operation sequence and operation identity.

Later BOM revisions must never rewrite a released production order.

## 4. Material consumption

For production quantity `Q` and BOM yield `Y`:

`planned component consumption = Q × component_quantity / Y`

Scrap allowance is tracked separately from normal planned consumption.

Actual inventory consumption must record:
- production order;
- frozen BOM version;
- component Product UUID;
- source stock/lot where available;
- actual quantity;
- unit;
- consumption timestamp;
- responsible actor.

Planned versus actual usage must remain available for variance analysis.

## 5. E.Y.T manufacturing route

The execution model must support routes such as:

1. raw-material purchase/receiving
2. cutting
3. forging
4. drilling
5. CNC machining
6. threading/tapping
7. black plating
8. assembly
9. final QC
10. finished-goods receipt

The reference E.Y.T production scenario is the Ario tie-rod-end body using CK45 steel Ø24 mm. The route is a template for operational traceability, not a hard-coded product-specific workflow.

## 6. Subcontracting

Every outsourced operation must record:
- contractor/supplier identity;
- operation code and sequence;
- dispatch date/time;
- input quantity;
- accepted quantity;
- rejected quantity;
- waste quantity and reason;
- service cost;
- transport cost;
- return/receipt date;
- supporting document reference.

An outsourced operation cannot be completed without a responsible contractor or accountable internal owner.

## 7. Quantity reconciliation

For every operation:

`input = accepted + rejected + waste + approved process variance`

Negative quantities are prohibited. Unexplained variance blocks completion.

## 8. Material sleep time

The production ledger must preserve material lifecycle timestamps needed to calculate material sleep/holding time:

`receiving → reservation → production issue → operation completion → finished-goods receipt`

Holding-cost calculations must use actual elapsed time and the capital basis defined by the costing contract. Customer prepayments, when linked to the production order, reduce the capital actually financed by E.Y.T.

## 9. QC handoff

Final QC must inspect the produced quantity before finished goods are released. Rejected/rework quantities remain traceable to the production order and operation that generated them.

A failed final QC result blocks normal finished-goods release.

## 10. Costing handoff

Production execution must expose:
- actual material cost;
- subcontractor/service cost;
- labor cost;
- transport cost;
- QC/rework/scrap cost;
- overhead allocations;
- capital holding cost;
- planned versus actual cost variance.

The cost record must retain links to the source production order, operation, material consumption and contractor transaction.

## 11. Audit and permissions

Production release, material issue, operation start/completion, subcontractor receipt, QC disposition, finished-goods receipt and cost adjustments are auditable mutations.

Permissions must prevent unauthorized production execution and cost alteration.

## 12. Acceptance gate

The integration is accepted only when a synthetic E.Y.T production order can complete this chain without identity duplication:

`Master Catalog → Approved BOM → Production Release → Material Consumption → Operations/Contractors → QC → Finished Goods → Costing → Audit`

PostgreSQL integration/E2E, ERP CI and Identity/RBAC CI must all be green before merge.
