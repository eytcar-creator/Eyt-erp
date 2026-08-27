# E.Y.T ERP Implementation Blueprint

## Purpose
Build the E.Y.T operating system so the company can run from purchasing raw materials through production, subcontracting, QC, warehouse, sales, collections and finance without daily CEO intervention.

## Existing repository baseline
The repository is `eytcar-creator/Eyt-erp` on branch `main`. The current structure is a scaffold with `api/`, `database/`, `docs/`, `excel/`, `images/`, `n8n/`, `odoo/`, `src/`, and `tests/`. This implementation preserves that structure and extends it rather than replacing it.

## Operating model
1. Request
2. Review
3. Approval
4. Execution
5. Verification
6. Audit
7. KPI / Exception

## Core modules
- Master Data
- Inventory & Warehouses
- Procurement & Suppliers
- Production & BOM
- Subcontractor Operations
- Quality Control
- Sales & CRM
- Delivery & Invoicing
- Receivables / Payables / Cash
- Authority & Approval Matrix
- Audit & Anti-Fraud Controls
- KPI / Exception Engine
- CEO Control Tower
- n8n Automation
- Odoo integration readiness

## Product Master rules
Every product should support:
- Product UUID
- SKU
- Persian and English names
- Category
- Vehicle/application
- OEM/reference numbers
- Barcode
- Unit of measure
- BOM / routing
- Standard cost
- Selling price
- Minimum margin
- Reorder point
- Active/inactive status

E.Y.T category rules:
- Ball joints: steering ball joint and lower-arm ball joint
- Bushes belong to suspension
- Three-prong/three-shakh is excluded from the E.Y.T master catalog

## Inventory model
Track at least:
- On hand
- Reserved
- Available
- Quarantine
- In production
- At subcontractor
- On purchase order

No uncontrolled stock adjustment or warehouse issue. Financial and stock transactions are reversed/cancelled rather than silently deleted.

## Procurement flow
Material Requirement -> Purchase Request -> RFQ -> Supplier Comparison -> Approval -> Purchase Order -> Receiving -> QC -> Inventory.

Controls include duplicate invoice detection, supplier risk, price variance, quantity variance and bank-account-change verification.

## Production flow
Production Order -> BOM -> Material Issue -> Operations -> Subcontractor where applicable -> QC -> Assembly -> Final QC -> Finished Goods Receipt.

Production must capture planned vs actual quantity, scrap, rework, material consumption, delays, responsible owner and completion date.

## Subcontractor control
Track material sent, expected return, actual return, approved scrap, rejected quantity, outstanding quantity, cost, lead time and aging. Variances create an exception case.

## Quality
QC remains independent from production. States include PASS, HOLD and FAIL. Returns follow Return Receipt -> QC -> Resalable / Rework / Scrap / Reject.

## Sales flow
Quotation -> Sales Order -> Credit Check -> Stock Check -> Reservation -> Delivery -> Invoice -> Collection.

Discounts and sales below minimum margin require the configured approval path.

## Finance
Maintain AR, AP, cash position, payment approvals, collection aging and bank reconciliation. Sensitive payments use document validation and dual control.

## Authority
Each action has a role, approval level, amount/risk threshold and escalation SLA. Sensitive actions separate REQUEST, APPROVE, EXECUTE and VERIFY where practical.

## Audit
Record who, what, when, old value, new value, reason and approver for material changes. Master data changes, stock adjustments, discounts, payments and supplier bank changes require audit history.

## CEO Control Tower
CEO view should prioritize:
- Sales
- Production
- Inventory
- Procurement
- Quality
- Cash
- Receivables
- Critical exceptions
- Decisions requiring CEO approval

Normal operations stay out of the CEO queue. Only exceptions and strategic decisions escalate.

## Autonomy KPIs
- CEO Dependency Rate = CEO interventions / operational decisions
- Exception Resolution Rate = issues resolved without CEO / total issues
- Process Compliance = compliant processes / total processes

Initial operating targets:
- CEO Dependency Rate < 5% for normal operations
- Exception Resolution Rate >= 90%
- Process Compliance >= 95%

## Implementation phases
### Phase 1
Database foundation and Product Master.

### Phase 2
Inventory, warehouses and stock ledger.

### Phase 3
Procurement and supplier management.

### Phase 4
Production, BOM, routing and subcontractors.

### Phase 5
Sales, CRM, delivery and invoicing.

### Phase 6
Finance integration and cash controls.

### Phase 7
Roles, permissions, approval workflows and audit.

### Phase 8
KPI, exception engine and CEO Control Tower.

### Phase 9
n8n automation and notifications.

### Phase 10
30-day autonomous-company test.

## Definition of done
A module is not complete until its data model, business rules, permissions, audit trail, tests and operational workflow are implemented and connected to the Control Tower where relevant.
