-- E.Y.T ERP | Inventory valuation and historical-status hardening
BEGIN;

CREATE OR REPLACE FUNCTION inventory_moving_average_at(
    p_warehouse_code VARCHAR,
    p_product_code VARCHAR,
    p_cutoff TIMESTAMPTZ
)
RETURNS TABLE(on_hand NUMERIC, average_cost NUMERIC, inventory_value NUMERIC)
LANGUAGE plpgsql AS $$
DECLARE
    r RECORD;
    q NUMERIC := 0;
    avg NUMERIC := 0;
    in_qty NUMERIC;
    in_cost NUMERIC;
BEGIN
    FOR r IN
        SELECT transaction_type, quantity, unit_cost, created_at, id
        FROM inventory_transactions
        WHERE warehouse_code=p_warehouse_code
          AND product_code=p_product_code
          AND created_at<=p_cutoff
          AND transaction_type <> 'RESERVE'
        ORDER BY created_at, id
    LOOP
        IF r.transaction_type IN ('RECEIPT','TRANSFER_IN','RETURN','PRODUCTION_RECEIPT','ADJUSTMENT') THEN
            in_qty := r.quantity;
            in_cost := COALESCE(r.unit_cost,0);
            IF q + in_qty > 0 THEN
                avg := ((q * avg) + (in_qty * in_cost)) / (q + in_qty);
            END IF;
            q := q + in_qty;
        ELSIF r.transaction_type IN ('ISSUE','TRANSFER_OUT','CONSUMPTION','SCRAP') THEN
            q := q - r.quantity;
            IF q < 0 THEN
                RAISE EXCEPTION 'Negative stock at %/% after transaction %', p_warehouse_code, p_product_code, r.id
                    USING ERRCODE='23514';
            END IF;
        END IF;
    END LOOP;
    on_hand := q;
    average_cost := CASE WHEN q > 0 THEN avg ELSE 0 END;
    inventory_value := q * average_cost;
    RETURN NEXT;
END;
$$;

CREATE TABLE IF NOT EXISTS inventory_reservation_events (
    id BIGSERIAL PRIMARY KEY,
    reservation_id VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL,
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    event_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS ix_inventory_reservation_events_history
    ON inventory_reservation_events(reservation_id,event_at,id);

CREATE OR REPLACE FUNCTION record_inventory_reservation_event()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='INSERT' THEN
        INSERT INTO inventory_reservation_events(reservation_id,status,quantity,event_at)
        VALUES(NEW.id::text,NEW.status,NEW.quantity,NEW.created_at);
    ELSIF TG_OP='UPDATE' AND (NEW.status IS DISTINCT FROM OLD.status OR NEW.quantity IS DISTINCT FROM OLD.quantity) THEN
        INSERT INTO inventory_reservation_events(reservation_id,status,quantity,event_at)
        VALUES(NEW.id::text,NEW.status,NEW.quantity,CURRENT_TIMESTAMP);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_inventory_reservation_history ON inventory_reservations;
CREATE TRIGGER trg_inventory_reservation_history
AFTER INSERT OR UPDATE ON inventory_reservations
FOR EACH ROW EXECUTE FUNCTION record_inventory_reservation_event();

INSERT INTO inventory_reservation_events(reservation_id,status,quantity,event_at)
SELECT r.id::text,r.status,r.quantity,r.created_at
FROM inventory_reservations r
WHERE NOT EXISTS (
    SELECT 1 FROM inventory_reservation_events e
    WHERE e.reservation_id=r.id::text
);

CREATE TABLE IF NOT EXISTS finished_goods_release_events (
    id BIGSERIAL PRIMARY KEY,
    release_id BIGINT NOT NULL,
    release_status VARCHAR(20) NOT NULL,
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0),
    consumed_qty NUMERIC(18,6) NOT NULL DEFAULT 0,
    event_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS ix_fg_release_events_history
    ON finished_goods_release_events(release_id,event_at,id);

CREATE OR REPLACE FUNCTION record_fg_release_event()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='INSERT' THEN
        INSERT INTO finished_goods_release_events(release_id,release_status,quantity,consumed_qty,event_at)
        VALUES(NEW.id,NEW.release_status,NEW.quantity,NEW.consumed_qty,NEW.released_at);
    ELSIF TG_OP='UPDATE' AND (
        NEW.release_status IS DISTINCT FROM OLD.release_status OR
        NEW.quantity IS DISTINCT FROM OLD.quantity OR
        NEW.consumed_qty IS DISTINCT FROM OLD.consumed_qty
    ) THEN
        INSERT INTO finished_goods_release_events(release_id,release_status,quantity,consumed_qty,event_at)
        VALUES(NEW.id,NEW.release_status,NEW.quantity,NEW.consumed_qty,CURRENT_TIMESTAMP);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_fg_release_history ON finished_goods_releases;
CREATE TRIGGER trg_fg_release_history
AFTER INSERT OR UPDATE ON finished_goods_releases
FOR EACH ROW EXECUTE FUNCTION record_fg_release_event();

INSERT INTO finished_goods_release_events(release_id,release_status,quantity,consumed_qty,event_at)
SELECT r.id,r.release_status,r.quantity,r.consumed_qty,r.released_at
FROM finished_goods_releases r
WHERE NOT EXISTS (
    SELECT 1 FROM finished_goods_release_events e WHERE e.release_id=r.id
);

COMMIT;