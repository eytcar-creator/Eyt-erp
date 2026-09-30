# E.Y.T Finance Notification Outbox v1

## Purpose

The finance alert engine creates an internal notification event before any external message is sent. This keeps the ERP ledger authoritative and prevents an email/SMS/WhatsApp failure from being mistaken for a financial settlement.

## Flow

ERP invoice and payment data
-> settlement alert sync
-> finance_settlement_alerts
-> finance_notification_outbox
-> external notification worker
-> Email / SMS / WhatsApp

## Alert types

- DUE_72H: open customer invoice due within 72 hours.
- DUE_24H: open customer invoice due within 24 hours.
- OVERDUE: open customer invoice past due date.

A fully collected invoice resolves its open settlement alert.

## Read endpoints

- GET /api/finance/alerts/summary
- GET /api/finance/alerts
- GET /api/finance/alerts/outbox

POST /api/finance/alerts/sync is the alert generation step and requires finance.write.

## Outbox event

Event type: FINANCE_SETTLEMENT_ALERT

The payload contains an alert identifier, invoice/customer identifiers, invoice number, due time, outstanding amount, severity and message.

The outbox record id is the idempotency key for an external sender. A sender must not treat an event as delivered merely because it was read from the outbox. Delivery should only be acknowledged after the provider confirms acceptance.

## Operational rule

The ERP remains the source of truth for receivables, payments, outstanding balances and alert state. External channels are delivery mechanisms only.

Do not mark an event SENT when an external provider is unavailable or returns an error. Keep it pending/retryable and preserve the provider error for operations review.
