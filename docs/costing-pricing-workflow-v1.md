# E.Y.T Costing → Pricing Workflow v1

## Flow
1. Register SKU.
2. Register direct materials and purchased components per unit.
3. Register workshop, packaging, freight, scrap, capital-sleep and other costs.
4. Calculate Actual Cost.
5. Apply SKU/product-family pricing coefficient.
6. Calculate MRP.
7. Calculate E.Y.T floor price.
8. Calculate channel prices.
9. Block prices below the floor unless central policy changes the rule.

## Standard channel ratios
- Consumer: 100% MRP
- Dealer: 85% MRP
- Distributor: 78% MRP
- Representative: 72% MRP
- Provincial representative / volume: 68% MRP

## Example: Haima S7 Qaraqari
Materials:
- Rod: 180,000
- Rubber: 15,000
- Grease: 5,000
- Cup: 75,000

Operational:
- Packaging: 24,000
- Workshop: 100,000

Actual Cost = 399,000 Tomans per unit.

With coefficient 1.40:
MRP = 558,600
With minimum E.Y.T margin 15%:
Floor = 458,850

Any calculated channel price below 458,850 is automatically raised to 458,850.
