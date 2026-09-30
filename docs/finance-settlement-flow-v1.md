# E.Y.T Finance Settlement Flow v1

## End-to-end control chain

Customer invoice
→ due date
→ outstanding balance
→ settlement alert
→ notification outbox
→ worker claim
→ dispatcher
→ provider
→ delivery result
→ retry / failed
→ queue health

## Financial controls

Customer collection and production/supplier payment remain separate ledger flows.

Funding sources are recorded independently and linked to payment records through the finance settlement bridge.

Notification delivery never changes financial balances.

## Alert policy

- DUE_72H: medium severity
- DUE_24H: high severity
- OVERDUE: high severity
- fully settled invoice: open alert is resolved

## Operational principle

The finance ledger is the source of truth. Notifications are an operational projection of that ledger, not a substitute for it.

If a provider is unavailable, the financial state remains unchanged and the notification remains retryable or failed according to the worker policy.
