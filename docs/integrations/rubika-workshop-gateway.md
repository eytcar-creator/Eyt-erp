# Rubika Workshop Gateway

The Rubika workshop group is an intake channel for the E.Y.T ERP.

## Flow

Rubika workshop group -> EYT Workshop AI Bot -> webhook -> ERP gateway -> raw message store -> AI extraction -> controlled ERP mutation.

## Endpoints

- GET /api/v1/integrations/rubika/workshop/health
- POST /api/v1/integrations/rubika/workshop/webhook

## Security

Set `RUBIKA_WORKSHOP_WEBHOOK_SECRET` in the production environment.

This secret is separate from the Rubika Bot Token. Never commit either secret to the repository.

The webhook accepts the secret through the `secret` query parameter or `X-Webhook-Secret` header.

## Data policy

Incoming messages are treated as raw operational evidence first. AI extraction may classify messages as payment, production, material, purchase, issue, or general, but this gateway does not directly mutate financial, inventory, or production records.

The canonical ERP record should only be created through the controlled workflow after validation/confirmation.

## Deployment checklist

1. Deploy the branch through the normal E.Y.T production process.
2. Set `RUBIKA_WORKSHOP_WEBHOOK_SECRET` in the production environment.
3. Run the database migration.
4. Verify the health endpoint.
5. Configure the Rubika bot webhook URL to the deployed endpoint.
6. Send a test message in the workshop group and verify raw intake before enabling AI extraction.
