# E.Y.T ERP End-to-End Execution Contract

This suite validates the operational business chain with synthetic data only.

## Flow
1. Authentication and RBAC
2. Product master
3. Purchase
4. Receiving
5. Inventory
6. Production order
7. Quality control
8. Costing
9. Sales order
10. Delivery
11. Receivables
12. Dashboard/reporting
13. Audit trail

## Definition of done
Every transition must persist successfully, enforce authorization, maintain inventory/financial invariants, and produce an auditable event. No production or customer data is used in CI.

The executable tests will be added incrementally against the existing API contracts rather than introducing a parallel ERP implementation.
