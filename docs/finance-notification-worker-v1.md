# E.Y.T Finance Notification Worker v1

## Objective
Consume finance_notification_outbox events and deliver them through configured external channels without changing the ERP financial ledger.

## State machine
PENDING -> PROCESSING -> SENT
PENDING -> PROCESSING -> FAILED -> PENDING (retry)
PENDING -> PROCESSING -> FAILED (terminal after retry policy)

## Delivery rules
1. Read only events whose status=PENDING and available_at <= now.
2. Claim an event atomically before delivery so two workers cannot send the same event.
3. Deliver to the configured provider.
4. Mark SENT only after the provider confirms acceptance.
5. On failure, increment attempts, store a safe error message in last_error, and set a future available_at using exponential backoff.
6. Never modify invoice balances, payment allocations, receivables, or settlement state as part of notification delivery.
7. Provider credentials must come from deployment secrets/environment variables, never from database payloads or source code.

## Channels
The first contract is channel-neutral: EMAIL, SMS, WHATSAPP.
The ERP produces one canonical event. Channel routing belongs to the notification worker.

## Recommended retry policy
- attempt 1: 1 minute
- attempt 2: 5 minutes
- attempt 3: 15 minutes
- attempt 4: 1 hour
- later attempts: capped delay

After the configured maximum attempts, leave the event FAILED and expose it to the operations dashboard.

## Security
Only the notification worker may transition outbox delivery states. Finance users can inspect the queue, but notification delivery must not be exposed as an unrestricted browser action.

## Current implementation boundary
E.Y.T currently has the producer and read-only outbox endpoint. The external sender is intentionally not marked as implemented until a provider connection and deployment worker are available.