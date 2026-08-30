# E.Y.T ERP — Final MVP Release Gate

## Purpose
Close the remaining operational roadmap items after the merged Product Master, Inventory, Procurement, QC, Costing, Sales, Delivery, Receivables, BOM and Production execution gates.

## Completed upstream gates
- Database migration chain hardened and verified
- Product Master / Master Catalog v2
- Inventory and canonical Product UUID identity
- Procurement and Receiving
- QC v2 contract
- Costing v2 contract
- Sales v2 contract
- Delivery v2 contract
- Receivables v2 contract
- BOM v2
- Production execution v2
- ERP CI and Identity/RBAC CI gates

## Final operational layer
The remaining release work is integration and deployment readiness, not creation of a second ERP architecture:

1. n8n automation uses ERP APIs and never writes competing product identities.
2. Odoo import/export maps canonical Product UUID, SKU and product_code.
3. Production deployment uses the existing Docker Compose stack.
4. Backup/restore is documented and executable with PostgreSQL tooling.
5. Health/readiness checks are mandatory after deployment.
6. No secrets, tokens, customer credentials or real business data are committed.

## E.Y.T end-to-end acceptance
A synthetic order must be traceable through:

Customer → Product/Vehicle Fitment → Inventory or Procurement → BOM → Production → Contractor Operations → QC → Finished Goods → Sales → Delivery → Invoice → Receivable → Payment → Dashboard/Audit

## Data safety invariants
- Product UUID is immutable.
- Inventory and BOM reference canonical Product UUID.
- Historical transactions retain original identity.
- QC rejection/rework cannot silently release stock as finished goods.
- n8n/Odoo integrations cannot create duplicate product identities.
- Production and financial events remain auditable.

## Release decision
Merge is allowed only when ERP CI, Identity/RBAC CI and PostgreSQL integration/E2E checks are green.

After merge, deploy only through the production compose configuration and run `/health` and `/ready` smoke checks before accepting real traffic.
