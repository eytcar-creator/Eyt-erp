# E.Y.T ERP Backend Production Hardening

## Scope

This document defines the production-hardening gate for the FastAPI/PostgreSQL backend. It is intentionally documentation-only until each executable control is implemented and covered by CI.

## Required gates

1. Configuration must fail closed when required production settings are missing.
2. `/health` must report process health without requiring a database transaction.
3. `/ready` must verify database connectivity before reporting readiness.
4. Database migrations must be deterministic and CI must reject broken migration chains.
5. Authentication and RBAC must remain enabled for protected operational endpoints.
6. Audit logging must capture security-sensitive and business-critical mutations.
7. Production containers must run without committed secrets or customer data.
8. Inventory, production, sales, procurement and finance mutations must be transaction-safe.
9. API contracts must remain compatible with the operational portal.
10. End-to-end smoke tests must cover the critical business path before merge.

## Release gate

A backend hardening change may be merged to `main` only when the complete CI suite and production-compose smoke test pass.

## Data safety

Real E.Y.T customer, credential, payment, or production data must never be committed to Git. Production data is introduced only through controlled environment configuration or an audited import process.
