# E.Y.T AI Finance Agent v1 — Implementation Contract

Status: design/implementation contract only. This document does not claim that a live agent, production connector, scheduled job, or database migration has been deployed.

## Objective

Deliver the first bounded E.Y.T AI Manager capability: a read-only daily finance and unit-economics briefing that prioritizes cash reality, verified costs, and working-capital exposure before recommending growth.

## Fit with the existing ERP

The ERP README describes a FastAPI + PostgreSQL application and an operational flow covering procurement, receiving, inventory, BOM, production, QC, sales, receivables, and dashboards. The agent must reuse those existing records and services. It must not create a parallel ledger or duplicate inventory/costing truth.

## Repository inspection findings (main branch, 2026-10-16)

The following existing implementation points were verified directly in the repository:

- API entry point: `api/production/main.py`; it already registers finance, cash-control, reconciliation, alerts, management, Profit First dashboard, inventory Profit First, costing, payable, and production routers.
- Existing Profit First read API: `GET /api/v1/profit-first/summary?days=30` and `GET /api/v1/profit-first/orders`, implemented in `api/production/profit_dashboard_api.py`. The summary reads `profit_first_order_control` and returns sales, COGS, gross profit, collected cash, receivables, operational cash contribution, margin and collection realization.
- Cash source ledger: `finance_funding_sources` and `finance_cash_movements`, defined by `database/migrations/20260930_finance_cash_control_v1.sql`. Movement status exists and must be filtered/labelled; a funding source's `current_balance` is a stored balance and should not be treated as reconciled bank truth without reconciliation evidence.
- CEO dashboard sources: `database/migrations/034_eyt_ceo_dashboard_actual_profit.sql` defines `cash_accounts`, `cash_transactions`, `receivables`, `ceo_cash_position`, `ceo_receivables`, `ceo_profit`, and `ceo_dashboard`. It links actual contribution to `eyt_order_actual_profitability`, and product/customer profitability views.
- Production actual cost source: `database/migrations/032_eyt_actual_cost_v1.sql` defines `eyt_snapshot_actual_production_cost` and `eyt_production_actual_cost`, using recorded material movements, operation service/transport, scrap, holding, packaging and overhead components.
- Finance read authorization already exists as `require_permission("finance.read")` in `api/production/auth.py`; migration 037 grants that permission to the CEO role.
- The production Compose file includes a finance worker for existing finance alert/notification synchronization. That is not evidence that the AI daily briefing or its scheduler exists.

### Implementation implications

- **Security follow-up:** the initial source review found that `api/production/profit_dashboard_api.py` did not visibly enforce `finance.read` on `/summary` and `/orders`. The feature branch now adds `Depends(require_permission("finance.read"))` to both handlers and adds a regression test in `tests/test_profit_dashboard_security.py`. This is branch-level work; CI must pass before treating it as verified or merged.
- **Data-model caution:** the CEO cash view currently reports aggregate cash transactions and net movement, not a reconciled point-in-time account balance. The daily brief must label this correctly and avoid presenting it as available cash.

1. Do not rebuild the Profit First summary or cost calculation. The new endpoint should compose existing canonical views/services where their date semantics and data completeness are verified.
2. Keep cash movement ledger and CEO `cash_transactions` distinct until the existing reconciliation bridge proves how they relate; never add both together.
3. Keep cash balance, net cash movement, collections, invoices, and forecast commitments as separate measures.
4. Treat `eyt_production_actual_cost` as a recorded production cost snapshot, not proof that every open order has a complete final cost. Missing or stale snapshots must be surfaced.
5. Before implementation, inspect the SQL definitions for `profit_first_order_control`, `eyt_order_actual_profitability`, and the settlement/reconciliation services. The first code change must not assume their grain, currency, or status semantics from their names alone.

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

## Initial API contract (implemented on the feature branch; not deployed)

The branch now registers `GET /api/v1/ai-finance/daily-brief?as_of=YYYY-MM-DD&window_days=30` in `api/production/ai_finance_api.py`. It is read-only, protected by `finance.read`, and includes regression tests. It is not merged or deployed.

Implementation boundaries:
- Cash actuals are recorded period movements from `cash_transactions`, not an available or reconciled balance.
- Currency is left null because the composed sources do not prove a shared currency.
- Payables are partial open settlement alerts only; total payables and forecast commitments remain unavailable.
- Working-capital valuations and cash forecasts return `INSUFFICIENT_DATA` until authoritative sources are verified.
- Actions are deterministic proposals with `status=PROPOSED`; no LLM, scheduler, or mutation is involved.

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