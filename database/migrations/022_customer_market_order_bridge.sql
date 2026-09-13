-- 022_customer_market_order_bridge.sql
-- Bridge confirmed customer sales orders into the Customer & Market Engine.
-- Keeps the consumer -> vehicle -> product -> order -> repeat-purchase chain in one source of truth.

CREATE UNIQUE INDEX IF NOT EXISTS ux_purchase_history_order_product
    ON purchase_history(order_id, product_id)
    WHERE order_id IS NOT NULL;

CREATE OR REPLACE FUNCTION sync_sales_order_to_customer_market()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_source TEXT;
BEGIN
    IF NEW.customer_id IS NULL OR COALESCE(NEW.status, '') = 'CANCELLED' THEN
        RETURN NEW;
    END IF;

    v_source := COALESCE(NULLIF(NEW.channel, ''), 'DIRECT');

    INSERT INTO purchase_history(
        customer_id,
        order_id,
        product_id,
        quantity,
        unit_price,
        source,
        notes
    )
    SELECT
        NEW.customer_id,
        NEW.id,
        soi.product_id,
        soi.quantity,
        soi.unit_price,
        v_source,
        'AUTO: Order Center → Customer & Market Engine'
    FROM sales_order_items soi
    WHERE soi.sales_order_id = NEW.id
    ON CONFLICT (order_id, product_id)
    WHERE order_id IS NOT NULL
    DO UPDATE SET
        quantity = EXCLUDED.quantity,
        unit_price = EXCLUDED.unit_price,
        source = EXCLUDED.source;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sales_order_customer_market_bridge ON sales_orders;

CREATE TRIGGER trg_sales_order_customer_market_bridge
AFTER INSERT OR UPDATE OF status, customer_id, channel
ON sales_orders
FOR EACH ROW
EXECUTE FUNCTION sync_sales_order_to_customer_market();

CREATE OR REPLACE FUNCTION sync_sales_order_item_to_customer_market()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_order sales_orders%ROWTYPE;
BEGIN
    SELECT * INTO v_order
    FROM sales_orders
    WHERE id = NEW.sales_order_id;

    IF v_order.id IS NULL OR v_order.customer_id IS NULL OR COALESCE(v_order.status, '') = 'CANCELLED' THEN
        RETURN NEW;
    END IF;

    INSERT INTO purchase_history(
        customer_id,
        order_id,
        product_id,
        quantity,
        unit_price,
        source,
        notes
    ) VALUES (
        v_order.customer_id,
        v_order.id,
        NEW.product_id,
        NEW.quantity,
        NEW.unit_price,
        COALESCE(NULLIF(v_order.channel, ''), 'DIRECT'),
        'AUTO: Order Center → Customer & Market Engine'
    )
    ON CONFLICT (order_id, product_id)
    WHERE order_id IS NOT NULL
    DO UPDATE SET
        quantity = EXCLUDED.quantity,
        unit_price = EXCLUDED.unit_price,
        source = EXCLUDED.source;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sales_order_item_customer_market_bridge ON sales_order_items;

CREATE TRIGGER trg_sales_order_item_customer_market_bridge
AFTER INSERT OR UPDATE OF quantity, unit_price, product_id, sales_order_id
ON sales_order_items
FOR EACH ROW
EXECUTE FUNCTION sync_sales_order_item_to_customer_market();

COMMENT ON TRIGGER trg_sales_order_customer_market_bridge ON sales_orders IS
'Automatically mirrors customer sales orders into purchase_history for Customer & Market Engine.';

COMMENT ON TRIGGER trg_sales_order_item_customer_market_bridge ON sales_order_items IS
'Automatically mirrors customer order lines into purchase_history for Customer & Market Engine.';
