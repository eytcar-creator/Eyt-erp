# E.Y.T Daily Pricing Engine

Independent pricing/costing component for daily repricing.

Every pricing run is based on inputs valid for that day. Material prices,
labor rates, overhead, setup/batch economics and scrap assumptions can change
without changing the Product Master or historical sales snapshots.

Cost layers:
1. Raw material
2. Purchased parts
3. Direct labor
4. Machine and energy
5. Subcontracting
6. Tooling
7. Batch setup allocation
8. Packaging
9. QC
10. Transport
11. Manufacturing overhead
12. Scrap/waste adjustment

Calculation flow:
true unit cost -> target-margin selling price -> channel prices

Selling price formula:
selling price = true unit cost / (1 - target margin)

Daily operating model:
- Open a new pricing run for the day.
- Enter or import current material and labor rates.
- Calculate affected SKUs.
- Review cost changes and margin.
- Publish the approved price list.
- Never overwrite a published run.

The component is intentionally independent from order, inventory and production
runtime. Those systems can later consume an approved pricing snapshot.
