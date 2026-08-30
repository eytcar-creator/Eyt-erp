# E.Y.T ERP — Receivables Operational V2

## Scope
Operational receivables flow from invoice issuance through due-date tracking, settlement, allocation, reconciliation, and audit.

## Flow
Invoice → Receivable → Due Date → Payment/Settlement → Allocation → Reconciliation → Outstanding Balance.

## Invariants
- Every receivable must reference an originating invoice/customer.
- Settlement amounts must be positive and cannot exceed the open balance unless explicitly handled as overpayment/credit.
- Allocation must not exceed the settlement amount or allocated receivable balance.
- Outstanding balance = invoice receivable − valid allocated settlements.
- Reversals and adjustments must be auditable and cannot silently rewrite history.
- Customer balance must reconcile with its receivable transactions.
- Receivable mutations require appropriate financial permission.

## Payment states
Open, Partially Paid, Paid, Overdue, Disputed, Written Off, and Reversed.

## Traceability
Invoice, customer, payment, allocation, user, timestamp, and adjustment reason must remain traceable.

## Release gate
Receivables is complete for this phase only when required executable tests and ERP/Identity CI checks are green.