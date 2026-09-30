# E.Y.T Finance Notification Worker Runtime v1

## Purpose

Run the finance notification worker as a bounded, repeatable job without modifying
the financial ledger.

## Command

`python scripts/run_finance_notification_worker.py --worker-id finance-worker-01 --limit 25`

## Required environment

- `DATABASE_URL`
- `FINANCE_NOTIFICATION_WORKER_ID` (optional when `--worker-id` is supplied)
- Provider-specific secrets are required only when a real notification provider is enabled.

## Recommended schedule

Run one bounded cycle every 1 minute.

The worker itself:
1. reclaims stale PROCESSING events older than 30 minutes;
2. claims up to the configured batch limit;
3. dispatches through the notification provider;
4. marks accepted deliveries SENT;
5. retries rejected/failed deliveries with bounded backoff;
6. moves exhausted events to FAILED;
7. reports queue health.

## Safety boundary

The worker does not update invoices, payments, receivables, payables, or funding
balances. It only updates notification outbox delivery state.

## Current provider state

The repository default remains DRY_RUN. A real EMAIL/SMS/WhatsApp provider must
be explicitly configured and verified before external delivery is enabled.

## Runtime acceptance checks

Before enabling a real scheduler:
- DATABASE_URL resolves to the intended PostgreSQL instance.
- finance notification migrations are applied.
- the worker can claim and release a test event.
- DRY_RUN processing produces no external message.
- retry and stale-event recovery are observable.
- queue health reports FAILED and stale PROCESSING counts.
