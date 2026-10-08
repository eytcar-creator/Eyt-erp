-- E.Y.T Daily Pricing Engine v1
-- Independent, immutable daily pricing snapshots.
-- Does not alter Product Master, production orders or sales prices.

CREATE TABLE IF NOT EXISTS pricing_runs (
    id BIGSERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','approved','published','superseded')),
    currency TEXT NOT NULL DEFAULT 'IRR',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pricing_runs_date_status_active
ON pricing_runs(run_date)
WHERE status IN ('draft','approved','published');

CREATE TABLE IF NOT EXISTS pricing_inputs (
    id BIGSERIAL PRIMARY KEY,
    pricing_run_id BIGINT NOT NULL REFERENCES pricing_runs(id) ON DELETE CASCADE,
    product_uuid UUID,
    product_code TEXT NOT NULL,
    material_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    purchased_parts_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    direct_labor_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    machine_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    energy_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    subcontracting_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    tooling_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    setup_total NUMERIC(18,2) NOT NULL DEFAULT 0,
    setup_batch_qty NUMERIC(18,4) NOT NULL DEFAULT 0,
    packaging_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    qc_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    transport_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    overhead_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
    scrap_rate NUMERIC(9,6) NOT NULL DEFAULT 0,
    accepted_qty NUMERIC(18,4) NOT NULL DEFAULT 1,
    source_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pricing_results (
    id BIGSERIAL PRIMARY KEY,
    pricing_run_id BIGINT NOT NULL REFERENCES pricing_runs(id) ON DELETE CASCADE,
    pricing_input_id BIGINT NOT NULL REFERENCES pricing_inputs(id) ON DELETE CASCADE,
    product_uuid UUID,
    product_code TEXT NOT NULL,
    true_unit_cost NUMERIC(18,2) NOT NULL,
    target_margin NUMERIC(9,6) NOT NULL,
    base_selling_price NUMERIC(18,2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'calculated'
        CHECK (status IN ('calculated','approved','published')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pricing_channel_results (
    id BIGSERIAL PRIMARY KEY,
    pricing_result_id BIGINT NOT NULL REFERENCES pricing_results(id) ON DELETE CASCADE,
    channel_code TEXT NOT NULL,
    discount_rate NUMERIC(9,6) NOT NULL DEFAULT 0,
    selling_price NUMERIC(18,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(pricing_result_id, channel_code)
);

CREATE INDEX IF NOT EXISTS idx_pricing_inputs_run_product
ON pricing_inputs(pricing_run_id, product_code);

CREATE INDEX IF NOT EXISTS idx_pricing_results_run_product
ON pricing_results(pricing_run_id, product_code);

CREATE INDEX IF NOT EXISTS idx_pricing_channels_result
ON pricing_channel_results(pricing_result_id);

CREATE OR REPLACE VIEW current_published_pricing AS
SELECT
    r.product_code,
    r.product_uuid,
    r.true_unit_cost,
    r.target_margin,
    r.base_selling_price,
    pr.run_date,
    pr.id AS pricing_run_id
FROM pricing_results r
JOIN pricing_runs pr ON pr.id = r.pricing_run_id
WHERE pr.status = 'published';

COMMENT ON TABLE pricing_runs IS
'E.Y.T independent daily pricing runs. Published runs are historical snapshots.';
