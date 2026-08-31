# E.Y.T Order Center Runtime

The Order Center is split into domain rules, persistence, HTTP routes, and automation events.

1. `order_center.py` — domain/application rules.
2. `postgres_adapter.py` and `atomic_confirm.py` — PostgreSQL persistence and atomic reservation boundary.
3. `fastapi_router.py` — HTTP API.
4. `events.py` — versioned automation events for n8n.

## Runtime wiring

At application startup, construct the PostgreSQL repository and inventory gateway with the ERP's existing database pool/connection and call `configure_order_center(service)` before `app.include_router(router)`.

The repository intentionally does not create a second connection pool. Transaction ownership stays with the ERP's existing PostgreSQL infrastructure.

## Atomic confirmation

Confirmation must use one PostgreSQL transaction for order lock, stock locks, availability checks, reservation, order status transition and audit. Any exception rolls the entire operation back.

## Automation

`events.py` defines versioned events for n8n or another event consumer. Consumers should treat events as at-least-once delivery and deduplicate using an event identifier when the transport provides one.

## Representative portal MVP

Dashboard, new order, order tracking and account/credit views are specified in `representative_portal.md`. Authorization is mandatory: representatives only see permitted customers and territory data.
