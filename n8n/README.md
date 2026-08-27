# E.Y.T ERP Automation Layer

This folder contains the n8n automation layer for E.Y.T ERP. Business transactions remain in the ERP database; n8n orchestrates events, notifications, SLA timers and escalation.

## Core Workflows

- `EYT-EXCEPTION-CRITICAL` - critical exception notification and escalation
- `EYT-PO-DELAY` - overdue purchase order follow-up
- `EYT-SUBCONTRACTOR-AGING` - materials held by subcontractors beyond SLA
- `EYT-QC-FAILURE` - QC failure, quarantine and NCR workflow
- `EYT-LOW-STOCK` - reorder-point alert and purchase recommendation
- `EYT-AR-OVERDUE` - overdue customer receivable follow-up
- `EYT-CEO-DECISION` - CEO approval and decision queue
- Customer Lead Automation
- Sales Order Automation
- Inventory Alerts
- WhatsApp Notifications
- Telegram Notifications
- Email Notifications
- CRM Automation
- Supplier Automation
- Dashboard Reports
- AI Assistant Integration

## Event Flow

ERP event -> n8n -> validation/idempotency -> business action -> notification -> SLA timer -> escalation -> ERP audit reference.

## Automation Principles

- Idempotent event handling and duplicate-notification protection
- Retry with backoff and an error/dead-letter path
- Correlation ID on every workflow
- Every external notification references the originating ERP transaction
- Escalation is SLA-based, not dependent on manual follow-up
- CEO receives exceptions and decisions, not routine operational noise
- Credentials, passwords and API keys must never be committed to Git

## Notification Channels

The implementation may connect configured WhatsApp, SMS, email, Telegram and in-app providers through n8n credentials. Provider-specific credentials belong in n8n's credential store/environment secrets.

## Initial Business Rules

### Critical exception
Create/receive critical exception -> notify owner -> start SLA -> escalate when overdue -> create/update CEO decision item.

### Purchase delay
Expected receipt date passes without receipt -> create operational alert -> notify procurement -> escalate according to SLA.

### Subcontractor aging
Expected return date passes while material remains with subcontractor -> alert production/procurement -> escalate if unresolved.

### QC failure
Inspection FAIL/HOLD -> quarantine affected stock -> notify QC/production -> open NCR -> block normal release until disposition.

### Low stock
Available stock falls below reorder point -> create purchase recommendation -> route for approval according to value/risk.

### Overdue receivable
Invoice reaches due date with balance -> create collection task -> reminder -> escalate by aging bucket.

### CEO decision
Policy requires CEO approval -> create decision queue item -> notify CEO -> record decision and audit trail.

© E.Y.T
