import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .operation_api import router as operation_router
from .production_control_api import router as production_control_router
from .auth import router as auth_router
from .costing_api import router as costing_router
from .dashboard_api import router as dashboard_router
from .sales_api import router as sales_router
from .procurement_api import router as procurement_router
from .finance_router import router as finance_router
from .commercial_api import router as commercial_router
from .inventory_flow_api import router as inventory_flow_router
from .product_master_api import router as product_master_router
from .vehicle_master_api import router as vehicle_master_router
from .public_catalog_api import router as public_catalog_router
from .purchase_receiving_api import router as purchase_receiving_router
from .qc_api import router as qc_router
from .profit_api import router as profit_router
from .payable_api import router as payable_router
from .customer_portal_api import router as customer_portal_router
from .customer_market_api import router as customer_market_router
from .repeat_purchase_api import router as repeat_purchase_router
from .cash_collection_api import router as cash_collection_router
from .profit_dashboard_api import router as profit_dashboard_router
from .strategy_action_api import router as strategy_action_router
from .strategy_users_api import router as strategy_users_router
from .strategy_notification_api import router as strategy_notification_router
from .crm_network_api import router as crm_network_router
from .inventory_api import router as inventory_router
from .core_master_api import router as core_master_router
from .inventory_production_api import router as inventory_production_router
from ..orders.fastapi_router import router as order_router, configure_order_center
from ..orders.order_center import OrderCenter
from ..orders.postgres_adapter import PostgresOrderRepository, PostgresInventoryGateway

app = FastAPI(title="E.Y.T ERP API", version="0.9.2")
app.include_router(inventory_router)
app.include_router(core_master_router)
app.include_router(inventory_production_router)
app.include_router(auth_router)
app.include_router(production_control_router)
app.include_router(operation_router)
app.include_router(costing_router)
app.include_router(dashboard_router)
app.include_router(sales_router)
app.include_router(procurement_router)
app.include_router(finance_router)
app.include_router(commercial_router)
app.include_router(inventory_flow_router)
app.include_router(product_master_router)
app.include_router(vehicle_master_router)
app.include_router(public_catalog_router)
app.include_router(purchase_receiving_router)
app.include_router(qc_router)
app.include_router(profit_router)
app.include_router(payable_router)
app.include_router(order_router)
app.include_router(customer_portal_router)
app.include_router(customer_market_router)
app.include_router(repeat_purchase_router)
app.include_router(cash_collection_router)
app.include_router(profit_dashboard_router)
app.include_router(strategy_action_router)
app.include_router(strategy_users_router)
app.include_router(strategy_notification_router)
app.include_router(crm_network_router)

def _configure_order_center() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return
    import psycopg
    def connection_factory():
        return psycopg.connect(database_url)
    orders = PostgresOrderRepository(connection_factory)
    inventory = PostgresInventoryGateway(connection_factory)
    configure_order_center(OrderCenter(orders, inventory))

_configure_order_center()
PORTAL = Path(__file__).resolve().parents[2] / "portal" / "index.html"
CEO_PORTAL = Path(__file__).resolve().parents[2] / "portal" / "ceo.html"

@app.get("/", include_in_schema=False)
def portal() -> FileResponse:
    return FileResponse(PORTAL)

@app.get("/ceo", include_in_schema=False)
def ceo_portal() -> FileResponse:
    return FileResponse(CEO_PORTAL)

@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "eyt-erp", "version": "0.9.2"}

@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    try:
        import psycopg
        with psycopg.connect(database_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database is not ready") from exc
    return {"status": "ready", "service": "eyt-erp", "version": "0.9.2"}
