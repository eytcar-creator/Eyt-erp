# E.Y.T AI Finance Agent v1 — Implementation Contract

Status: design/implementation contract only. This document does not claim that a live agent, production connector, scheduled job, or database migration has been deployed.

## Objective

Deliver the first bounded E.Y.T AI Manager capability: a read-only daily finance and unit-economics briefing that prioritizes cash reality, verified costs, and working-capital exposure before recommending growth.

## Fit with the existing ERP

The ERP README describes a FastAPI + PostgreSQL application and an operational flow covering procurement, receiving, inventory, BOM, production, QC, sales, receivables, and dashboards. The agent must reuse those existing records and services. It must not create a parallel ledger or duplicate inventory/costing truth.

## v1 outputs

- Cash position and cash movements, clearly separating posted/settled amounts from forecasts.
- Receivables: outstanding, overdue, aging buckets, and concentration by customer where supported by source data.
- Payables and near-term commitments where supported by source data.
- Product/order contribution using recorded revenue and recorded cost components only.
- Working-capital exposure in raw material, WIP, and finished goods only where reliable valuation data exists.
- Data-quality warnings for missing costs, stale prices, unmatched documents, duplicated source records, or incomplete production batches.
- A short action list ranked by expected cash impact, urgency, confidence, and reversibility.

## Calculation and data rules

1. Every numeric result must identify its source table/service, reporting period, currency/unit, and calculation basis.
2. Posted actuals, open commitments, and forecasts must be separate fields. Never present a forecast as cash on hand.
3. Use the ERP's authoritative cost and order-contribution logic where available; do not independently recalculate a competing official cost.
4. Missing or stale inputs must produce INSUFFICIENT_DATA, not a guessed value.
5. Do not assume Holoo is synchronized. A Holoo figure is usable only when an existing verified import/API and reconciliation status are available.
6. Do not infer margin from list price alone. Show revenue, recorded direct cost, known additional costs, and excluded/unknown costs separately.
7. All reports must be reproducible for the same source snapshot and period.

## Initial API contract (proposal; not yet implemented)

GET /api/v1/ai-finance/daily-brief?as_of=YYYY-MM-DD&window_days=30

Response envelope:
- as_of
- window_days
- generated_at
- source_snapshot (source names, timestamps, freshness)
- cash_actuals
- cash_forecast (if a validated forecast source exists)
- receivables
- payables
- product_contribution
- working_capital
- data_quality
- recommended_actions
- mutations_performed: false

Use existing authentication and RBAC. Restrict detailed customer and finance data to authorized roles. The first version is read-only and must not create, update, delete, post, pay, reserve, or approve financial records.

## Recommended-action policy

The agent may recommend an action and explain its evidence. It may not execute payments, change selling prices, place purchase orders, confirm sales orders, modify customer credit, or alter production plans. Any future write-capability requires a separately reviewed permission model, audit events, idempotency, and explicit approval gates.

Each recommendation should include:
- action_type
- summary
- estimated_cash_impact (nullable, with method)
- urgency
- confidence
- evidence_refs
- required_human_role
- status: PROPOSED

## Acceptance criteria

- Read-only behavior is tested; tests assert no finance, inventory, order, purchasing, or production mutation.
- Actual cash and forecast cash are never combined into one unlabeled figure.
- Missing cost or reconciliation data is surfaced as a warning and not silently imputed.
- Every KPI can be traced to source records and a documented formula.
- RBAC denies unauthorized users and does not expose detailed customer financial information.
- Tests cover empty periods, overdue receivables, missing costs, stale source data, duplicate imports, and zero/negative contribution.
- API tests and repository CI pass before merge.
- No production migration or deployment is performed as part of this initial read-only slice.

## Delivery sequence

1. Inspect and reuse existing finance, cash forecast, Profit First, costing, audit, and RBAC services.
2. Add the read-only response schema and source adapters without duplicating business rules.
3. Add unit/API tests and data-quality behavior.
4. Add a scheduled daily summary only after the endpoint and freshness checks are verified.
5. Connect notification delivery (for example, n8n/Rubika) only after secrets, recipient permissions, and failure handling are configured.

## Current boundary

This PR adds the contract for implementation review. It does not assert that data connectors, an endpoint, a scheduler, or notifications already exist or work in a live environment.