# E.Y.T System Map
Version: 1.0  
Status: Blueprint baseline / implementation specification  
Repository: `eytcar-creator/Eyt-erp`

## 1. Purpose

Define the shared data and workflow boundaries for E.Y.T's manufacturing, inventory, B2B/B2C commerce, mechanic network, warranty, marketing, and management systems. This document is a specification, not a claim that every module is already implemented.

## 2. Architecture principles

- One canonical Product Master and Vehicle/Fitment Master; modules must not maintain conflicting copies of core records.
- Every important business transaction has a stable ID, timestamp, responsible user/system, status, and audit history.
- Recommendations may be automated; consequential actions (price changes, production stop, recall, warranty decisions) require authorized approval.
- B2B and B2C share product, fitment, inventory, and order foundations, but use separate customer permissions and pricing rules.
- QR codes resolve to a secure product/serial/batch passport. Public product information must not expose customer personal data.
- SMS OTP/transactional notices are separate from promotional messaging. Promotional messages respect consent and opt-out.
- Kit/Pack BOMs are vehicle-specific where required. Never infer fitment or quantities without verified data.
- Manufacturing and sourcing reality must be represented accurately: do not mark a process as outsourced or available unless confirmed.

## 3. System map: input → processing → output → owner → connections

| Module | Inputs | Processing | Outputs | Primary owner | Connects to |
|---|---|---|---|---|---|
| Product Master | Product definitions, part numbers, dimensions, family, status | Validate uniqueness, classify, version | Product ID, SKU, technical record | Product/Admin | Fitment, BOM, stock, QR, pricing, QC |
| Vehicle & Fitment | Make/model/year/engine/gearbox/trim, axle/side, verified references | Compatibility review and approval | Fitment records with confidence/status | Technical/Product | Store, Kit Builder, mechanic app, QR |
| Pack & Kit Builder | Approved components, quantities, fitment, packaging | Validate BOM, component availability and substitutions | Pack/Kit SKU, BOM, contents list | Product/Sales | Pricing, inventory, B2B/B2C, QR |
| Pricing | Current material, labor, overhead, packaging, yield, margin and channel rules | Versioned cost calculation and price approval | Cost sheet, B2B price, B2C price, validity period | Finance/Management | Store, quotations, campaigns, production |
| Purchasing & Suppliers | Requisition, supplier quotes, lead time, quality history | Compare quotes, approvals, purchase order | PO, expected receipt, supplier score | Purchasing | Inventory, finance, production |
| Production & BOM | Approved production order, BOM, routing, capacity, materials | Plan operations, issue materials, report output/scrap/time | Work orders, actual costs, WIP, finished goods | Production | Purchasing, stock, QC, costing |
| Quality Control | Inspection plan, batch, measurements, defects | Inspect, accept/reject, corrective action | QC disposition, defect records, release status | QC | Production, stock, warranty, recall |
| Inventory & Warehouse | Receipts, issues, transfers, production output, reservations | Ledger-based stock updates and availability checks | On-hand, reserved, available, lot/batch traceability | Warehouse | Orders, purchasing, production, dashboards |
| B2B Portal | Verified trade account, product/fitment, quantity | Apply trade permissions/prices/credit rules | Quote and wholesale order | Sales | Product, pricing, stock, payment, CRM |
| B2C Store | Customer, saved vehicle, selected part/pack/kit | Fitment filtering, retail pricing, stock and shipping checks | Cart, order, payment and delivery status | E-commerce | Fitment, stock, payment, CRM, warranty |
| Customer Identity & OTP | Mobile number, OTP request, device/rate signals | Expiring one-time code, attempt limits, rate limits | Verified session and audit event | IT/Security | B2B, B2C, mechanic app |
| QR Product Passport | Product/serial/batch ID and public-safe product data | Resolve QR; check authenticity/status; role-aware access | Product info, authenticity state, warranty entry point | Product/IT | Customer, mechanic, seller, QC |
| Mechanic Network | Mechanic profile, shop details, verification and training | Role approval, installation workflow, performance tracking | Registered/Verified/Certified status | Service/Network Admin | QR, fitment, installation, warranty, CRM |
| Installation & Service History | QR/unit ID, vehicle, date, mileage, installer, optional evidence | Validate fitment and duplicate/invalid registration | Installation record and customer service history | Mechanic / Service | Warranty, customer garage, QC |
| Warranty & Claims | Sale, serial/batch, warranty terms, installation, evidence | Eligibility checks and authorized review | Claim status, decision, remedy, audit log | Warranty/QC | QR, orders, mechanic, quality |
| Recall & Quality Alerts | Claim trends, defect rates, batch and distribution trace | Threshold alerts, impact population, human approval | Investigation, stop-sale/recall case, notifications | Quality Lead/Management | QC, inventory, orders, CRM, SMS |
| CRM & Loyalty | Customer consent, purchases, vehicle, interactions, points | Segment customers, calculate eligible rewards | Customer timeline, loyalty balance, next-best offers | Marketing/CRM | B2C, B2B, campaigns, service |
| Campaigns, Events & SMS | Offer, audience, schedule, channel, budget, consent | Validate eligibility/consent, send, track outcomes | Delivery/click/conversion and campaign report | Marketing | CRM, pricing, store, SMS provider |
| Demand & Quality Intelligence | Sales, stock, lead times, claims, production and costs | Forecast, detect anomalies, calculate recommendations | Replenishment/quality/opportunity recommendations | Management/Analyst | Inventory, production, QC, finance |
| Decision Center & Dashboards | Approved operational events and metrics | Role-based views, priority ranking, approvals | Daily actions, decisions, audit trail | CEO / Department Leads | All modules |

## 4. Canonical identifiers and relationships

- `ProductID`: stable identity for a product definition.
- `SKU`: sellable stock-keeping code; Pack and Kit each receive their own SKU.
- `VehicleID` and `FitmentID`: normalized vehicle and approved compatibility records.
- `BOMID` / `BOMVersion`: versioned bill of materials for production or sales kits.
- `BatchID`: production/receipt lot for traceability.
- `UnitID`: unique serialized unit when unit-level tracking is enabled.
- `QRID`: opaque identifier that resolves to an authorized passport page; do not encode private data directly in the QR.
- `CustomerID`, `MechanicID`, `OrderID`, `InstallationID`, `WarrantyID`, `ClaimID`, `CampaignID`, `DecisionID`: stable business identifiers.

Core traceability:
`Product → BOM/Batch → Stock Movement → Order/Sale → Unit/QR → Installation → Warranty/Claim → QC Action`

## 5. Catalog rules that must be preserved

- Steering/suspension ball joints in this catalog are **سیبک فرمان** and **سیبک طبق**.
- Bushings belong under the relevant suspension/front-end family.
- **سه‌شاخ is not part of the E.Y.T catalog** and must not be added.
- Keep **بلبرینگ سرکمک** distinct from **توپی سرکمک**; do not rename it as «یاتاقان سرکمک».
- Model front/rear separately for **میل موج‌گیر** and **لاستیک چاکدار**.
- Model bushing size (small/large), axle, side, and vehicle fitment explicitly whenever applicable.
- Vehicle-specific quantities must come from verified BOMs, not assumed universal quantities.
- Radiator/heater hoses are hose products; do not classify them as rings.

## 6. Security, consent and audit

- Role-based access for customer, mechanic, B2B seller, warehouse, production, QC, finance, marketing, and administrator.
- OTP expiry, retry limits, throttling, and abuse logging.
- Keep authentication secrets and OTP values out of URLs and ordinary application logs.
- Separate transactional SMS from promotional campaigns; store consent source/time and opt-out status.
- Record who approved price changes, warranty outcomes, stop-sale/recall actions, and production decisions.
- Collect only installation photos and customer/vehicle data needed for the stated workflow; restrict access.

## 7. Delivery sequence

1. **Foundation audit:** inspect existing database migrations, API contracts, tests, and repository status before adding duplicate structures.
2. **Core master data:** Product, Vehicle, Fitment, supplier, warehouse, units of measure, and stable identifiers.
3. **BOM and costing:** versioned manufacturing BOMs, Kit/Pack BOMs, daily cost calculation, and pricing approvals.
4. **Inventory and production:** stock ledger, batch traceability, production orders, routing, QC release.
5. **Orders:** shared order core with B2B/B2C permissions, reservations, payments, shipment and returns.
6. **QR and warranty:** passport resolution, installation records, warranty rules and claim workflow.
7. **Mechanic PWA:** mobile QR scanner, installer onboarding, installation and claim evidence.
8. **CRM and campaigns:** consent-aware SMS, events, offers, loyalty and conversion measurement.
9. **Dashboards and intelligence:** operational KPIs first; forecasts and automated recommendations only after data quality is sufficient.

## 8. Definition of done for each module

A module is not complete merely because its screen exists. It must include:
- documented schema/API contract;
- validation and authorization;
- status transitions and audit events;
- tests for normal, invalid, duplicate, and permission-denied cases;
- integration with canonical IDs;
- migration/backward-compatibility considerations;
- observable errors and operational ownership.

## 9. Immediate next engineering task

Audit the current `Eyt-erp` repository and existing database/API implementation before creating more tables. Map existing entities to this document, list gaps, and implement the smallest non-duplicative slice: Product Master + Vehicle/Fitment references + validation/tests. Preserve existing approved commercial gates and read-only boundaries; do not introduce order, inventory, price, or production mutations into a read-only gate.
