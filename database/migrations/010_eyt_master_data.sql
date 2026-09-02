-- E.Y.T ERP | Migration 010 | E.Y.T Master Data foundation
-- Vehicle Master + Compatibility + Kit/Pack BOM + Price Master
-- PostgreSQL / idempotent
BEGIN;

CREATE TABLE IF NOT EXISTS vehicle_master (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id VARCHAR(60) NOT NULL UNIQUE,
    brand_id VARCHAR(60) NOT NULL,
    brand_name VARCHAR(100) NOT NULL,
    model_id VARCHAR(100) NOT NULL UNIQUE,
    model_name VARCHAR(150) NOT NULL,
    generation VARCHAR(150), platform VARCHAR(150), body_type VARCHAR(50),
    market VARCHAR(100) DEFAULT 'Iran', iran_manufacturer VARCHAR(150),
    production_start SMALLINT, production_end SMALLINT, engine_family VARCHAR(100),
    engine_code VARCHAR(100), displacement VARCHAR(50), fuel_type VARCHAR(40),
    aspiration VARCHAR(40), power VARCHAR(50), torque VARCHAR(50),
    transmission_type VARCHAR(50), transmission_code VARCHAR(100), drive_type VARCHAR(30),
    cylinders SMALLINT, valve_injection VARCHAR(100), trim VARCHAR(150), grade VARCHAR(100),
    body_configuration VARCHAR(100), doors SMALLINT, wheelbase VARCHAR(50),
    brake_configuration VARCHAR(150), suspension_configuration VARCHAR(150),
    steering_configuration VARCHAR(150), model_year VARCHAR(50), production_year VARCHAR(50),
    facelift VARCHAR(100), phase VARCHAR(100), vin_range VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE, notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_vehicle_compatibility (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    vehicle_id UUID NOT NULL REFERENCES vehicle_master(id) ON DELETE CASCADE,
    fitment_status VARCHAR(30) NOT NULL DEFAULT 'UNDER_REVIEW',
    position VARCHAR(60), side VARCHAR(30), engine_code VARCHAR(100), engine_volume VARCHAR(50),
    transmission VARCHAR(50), year_from SMALLINT, year_to SMALLINT, oem_reference VARCHAR(150),
    fitment_confidence VARCHAR(30) NOT NULL DEFAULT 'UNDER_REVIEW', notes TEXT,
    verified_by UUID, verified_at TIMESTAMPTZ, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (fitment_status IN ('CONFIRMED','PROBABLE','UNDER_REVIEW','REJECTED')),
    CHECK (fitment_confidence IN ('CONFIRMED','PROBABLE','UNDER_REVIEW','REJECTED')),
    CHECK (year_to IS NULL OR year_from IS NULL OR year_to >= year_from),
    UNIQUE(product_id, vehicle_id, position, side, year_from, year_to)
);

CREATE TABLE IF NOT EXISTS kit_bom_master (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    component_product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity NUMERIC(18,6) NOT NULL CHECK (quantity > 0), unit VARCHAR(20) NOT NULL DEFAULT 'PCS',
    required BOOLEAN NOT NULL DEFAULT TRUE, loss_percent NUMERIC(8,4) NOT NULL DEFAULT 0 CHECK (loss_percent >= 0),
    assembly_sequence INTEGER, qc_required BOOLEAN NOT NULL DEFAULT TRUE, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (parent_product_id <> component_product_id),
    UNIQUE(parent_product_id, component_product_id, assembly_sequence)
);

CREATE TABLE IF NOT EXISTS price_master (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    channel VARCHAR(30) NOT NULL, currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
    cost_basis NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (cost_basis >= 0),
    base_cost NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (base_cost >= 0),
    minimum_margin_percent NUMERIC(8,4) NOT NULL DEFAULT 0 CHECK (minimum_margin_percent >= 0),
    target_margin_percent NUMERIC(8,4) NOT NULL DEFAULT 0 CHECK (target_margin_percent >= 0),
    price_before_discount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (price_before_discount >= 0),
    discount_percent NUMERIC(8,4) NOT NULL DEFAULT 0 CHECK (discount_percent >= 0 AND discount_percent <= 100),
    final_price NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (final_price >= 0),
    effective_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, effective_to TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', approved_by UUID, approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (effective_to IS NULL OR effective_to > effective_from),
    CHECK (status IN ('DRAFT','ACTIVE','EXPIRED','CANCELLED')),
    CHECK (channel IN ('DISTRIBUTOR','DEALER','WHOLESALE','RETAIL'))
);

CREATE INDEX IF NOT EXISTS idx_vehicle_master_brand_model ON vehicle_master(brand_name, model_name);
CREATE INDEX IF NOT EXISTS idx_vehicle_master_active ON vehicle_master(is_active);
CREATE INDEX IF NOT EXISTS idx_compat_vehicle ON product_vehicle_compatibility(vehicle_id, fitment_status, is_active);
CREATE INDEX IF NOT EXISTS idx_compat_product ON product_vehicle_compatibility(product_id, fitment_status, is_active);
CREATE INDEX IF NOT EXISTS idx_bom_parent ON kit_bom_master(parent_product_id, is_active);
CREATE INDEX IF NOT EXISTS idx_bom_component ON kit_bom_master(component_product_id, is_active);
CREATE INDEX IF NOT EXISTS idx_price_product_channel ON price_master(product_id, channel, status, effective_from);

INSERT INTO product_categories(code,name_fa,name_en,parent_id)
SELECT 'SUSPENSION','جلوبندی و تعلیق','Suspension',NULL
WHERE NOT EXISTS (SELECT 1 FROM product_categories WHERE code='SUSPENSION');

INSERT INTO product_categories(code,name_fa,name_en,parent_id)
SELECT v.code,v.name_fa,v.name_en,p.id
FROM (VALUES
 ('STEERING_RACK_END','قرقری فرمان','Steering Rack End'),('STABILIZER_LINK','میل موجگیر','Stabilizer Link'),
 ('SLOTTED_BUSH','لاستیک چاکدار','Slotted Bush'),('CONTROL_ARM','طبق کامل','Complete Control Arm'),
 ('BOOT','گردگیر','Boot'),('ENGINE_MOUNT_BUSH','بوش دسته موتور','Engine Mount Bush'),
 ('KIT_SUSPENSION','کیت جلوبندی','Suspension Kit'),('PACK','پک','Pack')
) AS v(code,name_fa,name_en)
CROSS JOIN (SELECT id FROM product_categories WHERE code='SUSPENSION' LIMIT 1) p
WHERE NOT EXISTS (SELECT 1 FROM product_categories c WHERE c.code=v.code);

INSERT INTO vehicle_master(vehicle_id,brand_id,brand_name,model_id,model_name,body_type,market,is_active)
VALUES
('MVM-110','BR-MVM','MVM','MOD-MVM-110','110','Passenger','Iran',TRUE),('MVM-315','BR-MVM','MVM','MOD-MVM-315','315','Passenger','Iran',TRUE),
('MVM-X22','BR-MVM','MVM','MOD-MVM-X22','X22','SUV','Iran',TRUE),('MVM-X33','BR-MVM','MVM','MOD-MVM-X33','X33','SUV','Iran',TRUE),
('MVM-X55','BR-MVM','MVM','MOD-MVM-X55','X55','SUV','Iran',TRUE),('MVM-530','BR-MVM','MVM','MOD-MVM-530','530','Passenger','Iran',TRUE),
('MVM-550','BR-MVM','MVM','MOD-MVM-550','550','Passenger','Iran',TRUE),('JAC-S5','BR-JAC','JAC','MOD-JAC-S5','S5','SUV','Iran',TRUE),
('JAC-S3','BR-JAC','JAC','MOD-JAC-S3','S3','SUV','Iran',TRUE),('JAC-J4','BR-JAC','JAC','MOD-JAC-J4','J4','Passenger','Iran',TRUE),
('JAC-J5','BR-JAC','JAC','MOD-JAC-J5','J5','Passenger','Iran',TRUE),('CHERY-ARRIZO5','BR-CHERY','Chery','MOD-CHERY-ARRIZO5','Arrizo 5','Passenger','Iran',TRUE),
('CHERY-ARRIZO6','BR-CHERY','Chery','MOD-CHERY-ARRIZO6','Arrizo 6','Passenger','Iran',TRUE),('CHERY-TIGGO5','BR-CHERY','Chery','MOD-CHERY-TIGGO5','Tiggo 5','SUV','Iran',TRUE),
('CHERY-TIGGO7','BR-CHERY','Chery','MOD-CHERY-TIGGO7','Tiggo 7','SUV','Iran',TRUE),('CHERY-TIGGO7PRO','BR-CHERY','Chery','MOD-CHERY-TIGGO7PRO','Tiggo 7 Pro','SUV','Iran',TRUE),
('CHERY-TIGGO8','BR-CHERY','Chery','MOD-CHERY-TIGGO8','Tiggo 8','SUV','Iran',TRUE),('HAIMA-S5','BR-HAIMA','Haima','MOD-HAIMA-S5','S5','SUV','Iran',TRUE),
('HAIMA-S7-1800','BR-HAIMA','Haima','MOD-HAIMA-S7-1800','S7 1800','SUV','Iran',TRUE),('HAIMA-S7-2000','BR-HAIMA','Haima','MOD-HAIMA-S7-2000','S7 2000','SUV','Iran',TRUE),
('BRILLIANCE-H220','BR-BRILLIANCE','Brilliance','MOD-BRILLIANCE-H220','H220','Hatchback','Iran',TRUE),('BRILLIANCE-H230','BR-BRILLIANCE','Brilliance','MOD-BRILLIANCE-H230','H230','Passenger','Iran',TRUE),
('BRILLIANCE-H320','BR-BRILLIANCE','Brilliance','MOD-BRILLIANCE-H320','H320','Hatchback','Iran',TRUE),('BRILLIANCE-H330','BR-BRILLIANCE','Brilliance','MOD-BRILLIANCE-H330','H330','Passenger','Iran',TRUE),
('LIFAN-X50','BR-LIFAN','Lifan','MOD-LIFAN-X50','X50','SUV','Iran',TRUE),('LIFAN-X60','BR-LIFAN','Lifan','MOD-LIFAN-X60','X60','SUV','Iran',TRUE),
('LIFAN-520','BR-LIFAN','Lifan','MOD-LIFAN-520','520','Passenger','Iran',TRUE),('LIFAN-620','BR-LIFAN','Lifan','MOD-LIFAN-620','620','Passenger','Iran',TRUE),
('LIFAN-820','BR-LIFAN','Lifan','MOD-LIFAN-820','820','Passenger','Iran',TRUE),('ARIO-S300','BR-ARIO','Ario','MOD-ARIO-S300','S300','Passenger','Iran',TRUE),
('DONGFENG-H30','BR-DONGFENG','Dongfeng','MOD-DONGFENG-H30','H30 Cross','Hatchback','Iran',TRUE),('IKCO-TARA','BR-IKCO','Iran Khodro','MOD-IKCO-TARA','Tara','Passenger','Iran',TRUE),
('IKCO-DENA','BR-IKCO','Iran Khodro','MOD-IKCO-DENA','Dena','Passenger','Iran',TRUE),('IKCO-DENA-PLUS','BR-IKCO','Iran Khodro','MOD-IKCO-DENA-PLUS','Dena Plus','Passenger','Iran',TRUE),
('IKCO-PEUGEOT-2008','BR-IKCO','Iran Khodro','MOD-IKCO-PEUGEOT-2008','Peugeot 2008','SUV','Iran',TRUE),('IKCO-SUZUKI','BR-IKCO','Iran Khodro','MOD-IKCO-SUZUKI','Suzuki Grand Vitara','SUV','Iran',TRUE),
('SAIPA-SHAHIN','BR-SAIPA','Saipa','MOD-SAIPA-SHAHIN','Shahin','Passenger','Iran',TRUE),('CHANGAN-CS35','BR-CHANGAN','Changan','MOD-CHANGAN-CS35','CS35','SUV','Iran',TRUE),
('HYUNDAI-AZERA','BR-HYUNDAI','Hyundai','MOD-HYUNDAI-AZERA','Azera','Passenger','Iran',TRUE),('HYUNDAI-SONATA','BR-HYUNDAI','Hyundai','MOD-HYUNDAI-SONATA','Sonata','Passenger','Iran',TRUE),
('HYUNDAI-OTHER','BR-HYUNDAI','Hyundai','MOD-HYUNDAI-OTHER','Other Model','Passenger','Iran',TRUE),('KIA-RIO','BR-KIA','Kia','MOD-KIA-RIO','Rio','Passenger','Iran',TRUE),
('KIA-CERATO','BR-KIA','Kia','MOD-KIA-CERATO','Cerato','Passenger','Iran',TRUE),('TOYOTA-CAMRY','BR-TOYOTA','Toyota','MOD-TOYOTA-CAMRY','Camry','Passenger','Iran',TRUE),
('TOYOTA-RAV4','BR-TOYOTA','Toyota','MOD-TOYOTA-RAV4','RAV4','SUV','Iran',TRUE),('TOYOTA-HILUX','BR-TOYOTA','Toyota','MOD-TOYOTA-HILUX','Hilux','Pickup','Iran',TRUE),
('TOYOTA-PRADO','BR-TOYOTA','Toyota','MOD-TOYOTA-PRADO','Prado','SUV','Iran',TRUE),('TOYOTA-YARIS','BR-TOYOTA','Toyota','MOD-TOYOTA-YARIS','Yaris','Passenger','Iran',TRUE),
('NISSAN-MAXIMA','BR-NISSAN','Nissan','MOD-NISSAN-MAXIMA','Maxima','Passenger','Iran',TRUE),('NISSAN-RONIZ','BR-NISSAN','Nissan','MOD-NISSAN-RONIZ','Roniz','SUV','Iran',TRUE),
('NISSAN-TEANA','BR-NISSAN','Nissan','MOD-NISSAN-TEANA','Teana','Passenger','Iran',TRUE),('KMC-T8','BR-KMC','KMC','MOD-KMC-T8','T8','Pickup','Iran',TRUE),
('KMC-T9','BR-KMC','KMC','MOD-KMC-T9','T9','Pickup','Iran',TRUE),('KMC-J7','BR-KMC','KMC','MOD-KMC-J7','J7','Passenger','Iran',TRUE),
('GEELY-PASSENGER','BR-GEELY','Geely','MOD-GEELY-PASSENGER','Passenger','Passenger','Iran',TRUE),('GEELY-SUV','BR-GEELY','Geely','MOD-GEELY-SUV','SUV','SUV','Iran',TRUE),
('BESTURN-B30','BR-BESTURN','Besturn','MOD-BESTURN-B30','B30','Passenger','Iran',TRUE),('BESTURN-B50','BR-BESTURN','Besturn','MOD-BESTURN-B50','B50','Passenger','Iran',TRUE),
('FMC-511','BR-FMC','FMC','MOD-FMC-511','511','Passenger','Iran',TRUE),('MG-6','BR-MG','MG','MOD-MG-6','6','Passenger','Iran',TRUE),
('FOTON-SUV','BR-FOTON','Foton','MOD-FOTON-SUV','SUV','SUV','Iran',TRUE),('LAMARI-EAMA','BR-LAMARI','Lamari','MOD-LAMARI-EAMA','Eama','SUV','Iran',TRUE)
ON CONFLICT (vehicle_id) DO UPDATE SET brand_id=EXCLUDED.brand_id, brand_name=EXCLUDED.brand_name,
model_id=EXCLUDED.model_id, model_name=EXCLUDED.model_name, body_type=EXCLUDED.body_type,
market=EXCLUDED.market, is_active=EXCLUDED.is_active, updated_at=CURRENT_TIMESTAMP;

COMMIT;
