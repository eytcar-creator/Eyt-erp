# E.Y.T Order State Machine

Allowed forward flow:

`DRAFT -> PENDING_CONFIRMATION -> CONFIRMED -> RESERVED -> PREPARING -> READY_TO_SHIP -> SHIPPED -> DELIVERED`

Cancellation is allowed before shipment when business rules permit:

`DRAFT/PENDING_CONFIRMATION/CONFIRMED/RESERVED/PREPARING/READY_TO_SHIP -> CANCELLED`

Return flow:

`DELIVERED -> RETURNED`

Rules:
- No arbitrary status jumps.
- Reserved inventory must be released when a reserved order is cancelled.
- Shipped orders are never silently cancelled.
- Every transition creates an audit record.
- Automation events are emitted only after the transaction commits.
