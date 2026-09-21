-- E.Y.T ERP | Migration 038 | Network CRM foundation
-- Unifies B2C + B2B + channel identities + consent + relationship graph.
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS eyt_network_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_code VARCHAR(60) NOT NULL UNIQUE,
    entity_type VARCHAR(30) NOT NULL CHECK (entity_type IN (
        'CONSUMER','MECHANIC','RETAILER','DISTRIBUTOR','REPRESENTATIVE',
        'BRAND','SUPPLIER','FLEET','ORGANIZATION'
    )),
    display_name VARCHAR(250) NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    mechanic_id UUID REFERENCES mechanics(id) ON DELETE SET NULL,
    store_id UUID REFERENCES parts_stores(id) ON DELETE SET NULL,
    representative_id UUID REFERENCES representatives(id) ON DELETE SET NULL,
    phone VARCHAR(80),
    email VARCHAR(250),
    city VARCHAR(120),
    address TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE','BLOCKED')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_eyt_network_customer
    ON eyt_network_entities(customer_id) WHERE customer_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_eyt_network_mechanic
    ON eyt_network_entities(mechanic_id) WHERE mechanic_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_eyt_network_store
    ON eyt_network_entities(store_id) WHERE store_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_eyt_network_representative
    ON eyt_network_entities(representative_id) WHERE representative_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_eyt_network_type_city
    ON eyt_network_entities(entity_type, city, status);

CREATE TABLE IF NOT EXISTS eyt_channel_definitions (
    code VARCHAR(50) PRIMARY KEY,
    channel_type VARCHAR(30) NOT NULL CHECK (channel_type IN ('DIRECT','MARKETPLACE','MESSAGING','SOCIAL','SMS','PHONE','EMAIL','OTHER')),
    name_fa VARCHAR(120) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

INSERT INTO eyt_channel_definitions(code,channel_type,name_fa) VALUES
('EYT_DIRECT','DIRECT','فروش مستقیم E.Y.T'),
('TOROB','MARKETPLACE','ترب'),
('DIGIKALA','MARKETPLACE','دیجی‌کالا'),
('SNAPSHOP','MARKETPLACE','اسنپ‌شاپ'),
('BASALAM','MARKETPLACE','باسلام'),
('WHATSAPP','MESSAGING','واتساپ'),
('INSTAGRAM','SOCIAL','اینستاگرام'),
('TELEGRAM','MESSAGING','تلگرام'),
('SMS','SMS','پیامک'),
('BALE','MESSAGING','بله'),
('RUBIKA','MESSAGING','روبیکا'),
('PHONE','PHONE','تلفن'),
('EMAIL','EMAIL','ایمیل')
ON CONFLICT (code) DO UPDATE SET name_fa=EXCLUDED.name_fa, channel_type=EXCLUDED.channel_type;

CREATE TABLE IF NOT EXISTS eyt_channel_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES eyt_network_entities(id) ON DELETE CASCADE,
    channel_code VARCHAR(50) NOT NULL REFERENCES eyt_channel_definitions(code),
    external_id VARCHAR(250),
    handle VARCHAR(250),
    normalized_contact VARCHAR(250),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE(channel_code, external_id),
    UNIQUE(channel_code, normalized_contact)
);

CREATE INDEX IF NOT EXISTS idx_eyt_channel_identity_entity
    ON eyt_channel_identities(entity_id, channel_code);

CREATE TABLE IF NOT EXISTS eyt_marketing_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES eyt_network_entities(id) ON DELETE CASCADE,
    channel_code VARCHAR(50) NOT NULL REFERENCES eyt_channel_definitions(code),
    purpose VARCHAR(40) NOT NULL CHECK (purpose IN ('MARKETING','SERVICE','TRANSACTIONAL')),
    granted BOOLEAN NOT NULL,
    source VARCHAR(80),
    granted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE(entity_id, channel_code, purpose)
);

CREATE TABLE IF NOT EXISTS eyt_network_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_entity_id UUID NOT NULL REFERENCES eyt_network_entities(id) ON DELETE CASCADE,
    to_entity_id UUID NOT NULL REFERENCES eyt_network_entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN (
        'SERVICES','REFERS','BUYS_FROM','SUPPLIES_TO','DISTRIBUTES_FOR',
        'REPRESENTS','SELLS_FOR','WORKS_WITH','OWNS','MANAGES','MEMBER_OF'
    )),
    territory VARCHAR(120),
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_entity_id,to_entity_id,relationship_type,valid_from),
    CHECK (from_entity_id <> to_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_eyt_relationship_from
    ON eyt_network_relationships(from_entity_id, relationship_type);
CREATE INDEX IF NOT EXISTS idx_eyt_relationship_to
    ON eyt_network_relationships(to_entity_id, relationship_type);

CREATE TABLE IF NOT EXISTS eyt_channel_attribution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES eyt_network_entities(id) ON DELETE CASCADE,
    channel_code VARCHAR(50) NOT NULL REFERENCES eyt_channel_definitions(code),
    attribution_type VARCHAR(30) NOT NULL CHECK (attribution_type IN ('FIRST_TOUCH','LAST_TOUCH','ORDER_SOURCE','REFERRAL')),
    first_order_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_eyt_attribution_entity
    ON eyt_channel_attribution(entity_id, attribution_type, captured_at);

CREATE TABLE IF NOT EXISTS eyt_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_code VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','ACTIVE','PAUSED','ENDED')),
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    target_entity_type VARCHAR(30),
    target_channel_code VARCHAR(50) REFERENCES eyt_channel_definitions(code),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eyt_service_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES eyt_network_entities(id) ON DELETE CASCADE,
    vehicle_id UUID,
    product_id UUID,
    reminder_type VARCHAR(50) NOT NULL,
    due_date DATE,
    mileage_due_km INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CONTACTED','COMPLETED','CANCELLED')),
    source_order_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO eyt_permissions(code) VALUES ('crm.read'),('crm.write')
ON CONFLICT (code) DO NOTHING;

INSERT INTO eyt_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM eyt_roles r CROSS JOIN eyt_permissions p
WHERE r.name='CEO' AND p.code IN ('crm.read','crm.write')
ON CONFLICT DO NOTHING;

COMMIT;
