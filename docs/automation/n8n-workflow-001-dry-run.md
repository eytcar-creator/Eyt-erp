# n8n Workflow 001 - Sales Order Notification (Dry Run)

## Goal

Process one claimed automation event through the complete control path without sending a real customer message.

## n8n node sequence

1. **Schedule Trigger**
   - Run every 30 seconds.
   - No webhook/database polling from n8n.

2. **HTTP Request - Claim Events**
   - Method: POST
   - URL: `{{EYT_API_BASE}}/api/v1/automation/events/claim?limit=10&worker=n8n-order-notify`
   - Authentication: n8n credential with `automation.write`.

3. **Split Out - Events**
   - One item per claimed event.

4. **IF - Supported Event**
   - Accept:
     - `sales_orders.insert`
     - `sales_orders.update`
   - Unsupported events go directly to ACK/ignore handling.

5. **HTTP Request - Read Order**
   - Use the official Order Center/ERP order endpoint.
   - The endpoint must be selected from the existing E.Y.T API contract. Do not query PostgreSQL.
   - The order ID/order number comes from the claimed event.

6. **HTTP Request - Resolve Customer**
   - Use the CRM/network API.
   - Resolve customer UUID and channel identities.
   - Prefer an already-consented channel identity.

7. **Code/Set - Notification Policy**
   - Map current order state to a notification action.
   - If there is no customer-facing transition, mark the event as no-op and ACK.
   - In dry-run mode, never call a provider.

8. **HTTP Request - Reserve Effect**
   - Method: POST
   - URL: `{{EYT_API_BASE}}/api/v1/automation/effects/reserve`
   - Body:
```json
{
  "idempotency_key": "notification:{{$json.event_id}}:{{$json.channel}}:{{$json.action_code}}",
  "event_id": "{{$json.event_id}}",
  "channel": "{{$json.channel}}",
  "action_code": "{{$json.action_code}}"
}
```

9. **IF - Should Send**
   - Continue only when `should_send == true`.
   - If false because an existing effect is already SENT, do not send again.

10. **Dry Run**
   - Record the intended provider/channel/template in the n8n execution data.
   - No SMS/WhatsApp/Telegram provider call.

11. **HTTP Request - Complete Effect**
   - Mark the reserved effect as `SENT` only for a genuine provider delivery.
   - For dry-run, use a distinct future status or leave the effect as PROCESSING until the dry-run contract is replaced by real delivery.
   - Do not falsely record a customer message as sent.

12. **HTTP Request - CRM Activity**
   - Only after real delivery.
   - Record event ID, channel, action code and provider message ID.

13. **HTTP Request - ACK Event**
   - ACK only after all required processing is complete.
   - For dry-run, ACK is allowed only if the workflow explicitly treats dry-run as successful processing without a customer-facing side effect.

14. **Error path**
   - HTTP/API transient errors -> `POST /events/{event_id}/fail`.
   - Preserve the error message.
   - Allow the outbox `available_at` retry mechanism to reschedule processing.

## Important implementation rule

Do not use a generic HTTP node that sends a message before the effect reservation succeeds.

The required order is:

```
CLAIM
  ↓
AUTHORITATIVE ORDER READ
  ↓
CUSTOMER/CHANNEL RESOLUTION
  ↓
RESERVE EFFECT
  ↓
IF should_send
  ↓
PROVIDER SEND
  ↓
COMPLETE EFFECT
  ↓
CRM ACTIVITY
  ↓
ACK
```

## Production activation gate

The workflow remains DRY RUN until all are verified:

- EYT API reachable from n8n
- authentication works
- claim endpoint returns events
- order endpoint returns authoritative state
- CRM resolution returns channel identities
- effect reservation is unique and race-safe
- one provider can be called successfully
- provider delivery ID is stored
- CRM activity is recorded
- ACK changes event state
- retry after provider timeout does not create a duplicate send

## First channel

The architecture is channel-neutral. The first real provider should be connected only after the dry-run path and idempotency behavior are verified. No provider is hard-coded into the ERP.
