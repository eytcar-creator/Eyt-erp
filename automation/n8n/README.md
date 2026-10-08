# E.Y.T One Automation Hub (n8n)

n8n is the automation/integration layer around E.Y.T One. It is **not** the source of truth for orders, inventory, finance, production or QC.

## Runtime boundary

```
Channel -> n8n -> POST /api/v1/channel-intake -> E.Y.T One -> ERP/PostgreSQL
                         |
                         +-> customer/product resolution
                         +-> pending confirmation
                         +-> confirmed order -> reservation/credit controls
```

## First workflow

`eyt-one-channel-intake.json` exposes a generic webhook that forwards normalized channel payloads to the ERP Channel Hub.

Import the workflow into n8n, set:

- `EYT_ERP_API_BASE_URL` = ERP API base URL
- keep n8n behind HTTPS/reverse proxy
- protect the webhook at the edge before exposing it publicly

## Rules

- n8n may transform, route, notify and call APIs.
- n8n must not directly write ERP/PostgreSQL tables.
- Order confirmation must go through E.Y.T One.
- Inventory reservation and credit controls remain atomic inside the ERP.
- Channel adapters must use official APIs/webhooks. No scraping or unofficial account automation.
- Workflow executions are at-least-once. Use idempotency keys for every inbound message.

## Production deployment

The production compose file includes n8n under the `automation` profile so the ERP core is not made dependent on n8n availability.

```bash
docker compose -f docker-compose.production.yml --profile automation up -d n8n
```

The n8n database is isolated from the ERP PostgreSQL database. Do not point n8n at the ERP database.
