-- E.Y.T Order Center runtime schema
CREATE TABLE IF NOT EXISTS sales_orders (
  id BIGSERIAL PRIMARY KEY,
  order_no TEXT NOT NULL UNIQUE,
  customer_id UUID NOT NULL,
  representative_id UUID NULL,
  warehouse_code TEXT NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('WEBSITE','WHATSAPP','PHONE','INSTAGRAM','SHOP','REPRESENTATIVE','OTHER')),
  status TEXT NOT NULL DEFAULT 'PENDING_CONFIRMATION',
  idempotency_key TEXT UNIQUE,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  confirmed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales_order_items (
  id BIGSERIAL PRIMARY KEY,
  order_no TEXT NOT NULL REFERENCES sales_orders(order_no) ON DELETE CASCADE,
  product_id UUID NOT NULL,
  quantity NUMERIC(18,3) NOT NULL CHECK (quantity > 0),
  unit_price NUMERIC(18,2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE IF NOT EXISTS order_audit_log (
  id BIGSERIAL PRIMARY KEY,
  order_no TEXT NOT NULL,
  event_type TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sales_orders_customer ON sales_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_orders_status ON sales_orders(status);
CREATE INDEX IF NOT EXISTS idx_sales_order_items_product ON sales_order_items(product_id);

-- Sequence-backed human-readable E.Y.T order number.
CREATE SEQUENCE IF NOT EXISTS eyt_order_no_seq START 1;

CREATE OR REPLACE FUNCTION generate_eyt_order_no()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.order_no IS NULL OR NEW.order_no = '' THEN
    NEW.order_no := 'EYT-ORD-' || TO_CHAR(CURRENT_DATE, 'YYYY') || '-' || LPAD(nextval('eyt_order_no_seq')::TEXT, 6, '0');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sales_orders_order_no ON sales_orders;
CREATE TRIGGER trg_sales_orders_order_no
BEFORE INSERT ON sales_orders
FOR EACH ROW EXECUTE FUNCTION generate_eyt_order_no();
