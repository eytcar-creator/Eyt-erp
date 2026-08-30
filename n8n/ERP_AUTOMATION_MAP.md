# E.Y.T ERP n8n Automation Map

n8n is the automation layer around the ERP API. It must not become a second database.

## Initial workflows

### Inventory Alert
Trigger: scheduled or ERP event.
- Read low-stock/reorder candidates from ERP API.
- Filter by active Product UUID.
- Send notification to the configured operational channel.
- Record correlation/audit reference.

### Production/QC Alert
Trigger: production or QC event.
- Notify when an operation blocks, a quantity variance occurs, or QC rejects/reworks a batch.
- Never directly release finished goods.

### Sales/Receivables Notification
Trigger: sales order, delivery confirmation, invoice or payment event.
- Notify the responsible role.
- Include canonical order/invoice/customer references.

## Integration rules
- Authenticate with environment-managed credentials.
- Never store secrets in GitHub.
- Use idempotency/correlation IDs for retries.
- Treat ERP as the source of truth.
- Do not create products from free-text webhook payloads.
- All write actions must use canonical Product UUID/order identifiers.
