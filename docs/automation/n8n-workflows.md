# E.Y.T n8n Automation Workflows

## Purpose

n8n is the E.Y.T automation/integration layer. It orchestrates notifications, follow-up, channel delivery and external integrations. It is not the system of record for products, inventory, orders, production, QC or accounting.

**Rule:** n8n must never write directly to ERP/CRM database tables. It uses authenticated E.Y.T APIs.

## Workflow 001: Sales Order Event -> Customer Notification

### Trigger

Database changes on `sales_orders` emit an event into `eyt_automation_events`.

Relevant event types:
- `sales_orders.INSERT`
- `sales_orders.UPDATE`

The event payload is the controlled event contract. n8n must not reconstruct order state from database tables.

### Event contract

Minimum fields:

```json
{
  "event_id": "UUID",
  "event_type": "sales_orders.INSERT",
  "aggregate_type": "sales_order",
  "aggregate_id": "UUID-or-order-id",
  "source_table": "sales_orders",
  "occurred_at": "ISO-8601",
  "payload": {
    "order_id": "UUID",
    "order_no": "EYT-...",
    "customer_id": "UUID",
    "status": "PENDING"
  }
}
```

The database event ID is the primary idempotency key. Never use order number alone because an order can legitimately produce multiple lifecycle events.

## Processing sequence

1. **Claim**
   - n8n calls `POST /api/v1/automation/events/claim`.
   - Claim only `PENDING` events whose `available_at <= now()`.
   - The API uses `FOR UPDATE SKIP LOCKED`.
   - Worker identity is stored in `locked_by`.
   - Attempts are incremented atomically.

2. **Validate**
   - Confirm `event_id`, `event_type`, `aggregate_type` and `aggregate_id`.
   - Ignore unsupported event types and ACK them as `IGNORED`.

3. **Resolve customer**
   - Use the official CRM/network API to resolve the customer/network entity and available channel identities.
   - Do not query CRM tables directly.

4. **Read authoritative order state**
   - Fetch the order through the official Order Center/ERP API.
   - Treat the current API response as authoritative for the notification decision.
   - Do not trust stale event payload fields for price, stock, payment or final status.

5. **Determine notification**
   - Map order state to a notification policy.
   - Example states: received, confirmed, production, ready, shipped, delivered, cancelled.
   - Do not send customer-facing messages for internal-only changes.

6. **Idempotency gate**
   - External notification delivery must have its own idempotency key:
     `notification:{event_id}:{channel}:{template_code}`
   - The same key must never produce two intentional sends.
   - If a delivery record already exists as sent, skip delivery and continue to ACK.

7. **Send**
   - Use the appropriate channel adapter/API.
   - WhatsApp/SMS/Telegram/etc. remain channel-specific delivery mechanisms.
   - n8n owns orchestration, not customer identity.

8. **CRM activity**
   - Record the outbound interaction through the CRM API, including event ID, channel, template and delivery result.
   - This creates the audit trail without allowing n8n to mutate CRM tables directly.

9. **ACK**
   - On successful processing, call the automation ACK endpoint.
   - Store delivery IDs/results in the controlled automation/CRM layer.

10. **Failure**
   - On transient failure, call the fail endpoint with an error and retryable status.
   - Exponential backoff is preferred.
   - On permanent failure or exhausted attempts, route to an operational alert/dead-letter process.

## Idempotency requirements

Idempotency is required at two levels:

### Event processing
`event_id` prevents the same outbox event from being processed as a new event after a retry.

### External side effects
Every outbound message/action must have a deterministic key derived from:
- event ID
- channel
- action/template

Recommended logical key:

```
event_id + ":" + channel + ":" + action_code
```

A retry after timeout must first check whether that key has already been recorded as delivered. This protects against the classic "the API timed out but actually sent the SMS" problem.

## Retry policy

- Attempt 1: immediate retry for transient network/provider errors.
- Attempt 2: short backoff.
- Attempt 3: longer backoff.
- Further retries: controlled by `available_at` and an operational limit.
- Authentication, validation and permanent provider errors should not be blindly retried.

## Security

n8n credentials must contain API credentials/secrets only. Never place:
- JWT secrets
- database passwords
- payment credentials
- private ERP database connection strings

inside workflow data or customer-facing payloads.

Use least-privilege automation credentials. Separate read and write permissions where practical.

## Workflow boundary

```
ERP / CRM
    |
    v
Event Outbox
    |
    v
n8n
    +--> Customer/CRM resolution via API
    +--> Order state via API
    +--> Channel delivery
    +--> CRM activity via API
    |
    v
ACK / FAIL
```

n8n must **not** become a second ERP.

## Initial implementation order

1. Event claim
2. Order-state read
3. Customer/channel resolution
4. Idempotency record
5. One notification channel
6. CRM activity
7. ACK/FAIL
8. Retry/dead-letter handling
9. Additional channels

The first production channel should be enabled only after the complete dry-run path is verified.
