# Order Center Runtime

The Order Center is now split into three layers:

1. `order_center.py` — domain/application rules.
2. `postgres_adapter.py` — PostgreSQL persistence and inventory reservation boundary.
3. `fastapi_router.py` — HTTP API contract.

## Runtime wiring

At application startup, construct the PostgreSQL repository and inventory gateway with the project's existing database connection/pool, then call:

```python
from api.orders.fastapi_router import configure_order_center, router
from api.orders.order_center import OrderCenter

service = OrderCenter(order_repository, inventory_gateway)
configure_order_center(service)
app.include_router(router)
```

The repository intentionally does not create its own connection pool. This prevents a second pool from being created and keeps transaction ownership with the ERP's existing PostgreSQL infrastructure.

## Required transaction behavior

The concrete PostgreSQL adapter must keep order confirmation, stock locking/reservation, status transition and audit insertion inside one transaction. If any step fails, the transaction rolls back.
