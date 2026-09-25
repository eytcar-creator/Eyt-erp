-- EYT Master Product Tree v1.1
-- Migration 030
-- Seed canonical subfamilies and expose hierarchy/capacity semantics to runtime APIs.
-- Additive only.

INSERT INTO eyt_product_subfamily (family_id, code, name_fa, name_en, default_product_type, sort_order)
SELECT f.id, x.code, x.name_fa, x.name_en, x.product_type, x.sort_order
FROM eyt_product_family f
JOIN (VALUES
 ('STEERING','STEERING_BALL_JOINT','سیبک فرمان','Tie Rod End','FINISHED',10),
 ('STEERING','AXIAL_JOINT','قرقری','Axial Joint','FINISHED',20),
 ('STEERING','TIE_ROD_ASSEMBLY','مجموعه فرمان','Tie Rod Assembly','FINISHED',30),
 ('FRONT_SUSPENSION','FRONT_STABILIZER_LINK','موجگیر جلو','Front Stabilizer Link','FINISHED',10),
 ('FRONT_SUSPENSION','REAR_STABILIZER_LINK','موجگیر عقب','Rear Stabilizer Link','FINISHED',20),
 ('FRONT_SUSPENSION','CONTROL_ARM_BALL_JOINT','سیبک طبق','Control Arm Ball Joint','FINISHED',30),
 ('FRONT_SUSPENSION','STABILIZER_COMPONENTS','متعلقات موجگیر','Stabilizer Components','FINISHED',40),
 ('BUSHINGS','SMALL_CONTROL_ARM_BUSH','بوش طبق کوچک','Small Control Arm Bushing','FINISHED',10),
 ('BUSHINGS','LARGE_CONTROL_ARM_BUSH','بوش طبق بزرگ','Large Control Arm Bushing','FINISHED',20),
 ('BUSHINGS','STABILIZER_BUSH','بوش موجگیر','Stabilizer Bushing','FINISHED',30),
 ('BUSHINGS','SELECTED_SUSPENSION_BUSH','سایر بوش‌های منتخب','Selected Suspension Bushing','FINISHED',40),
 ('MOUNTING','ENGINE_MOUNT','دسته موتور','Engine Mount','FINISHED',10),
 ('MOUNTING','TRANSMISSION_MOUNT','دسته گیربکس','Transmission Mount','FINISHED',20),
 ('MOUNTING','SHOCK_ABSORBER_MOUNT','توپی سرکمک','Shock Absorber Mount','FINISHED',30),
 ('BELLOWS_RUBBER','STEERING_BELLOW','گردگیر فرمان','Steering Bellow','FINISHED',10),
 ('BELLOWS_RUBBER','AXLE_BELLOW','گردگیر پلوس','Axle Bellow','FINISHED',20),
 ('BELLOWS_RUBBER','SHOCK_ABSORBER_BELLOW','گردگیر کمک','Shock Absorber Bellow','FINISHED',30),
 ('BELLOWS_RUBBER','SLOTTED_RUBBER','لاستیک چاکدار','Slotted Rubber','FINISHED',40),
 ('BELLOWS_RUBBER','BUMP_STOP','ضربه‌گیر','Bump Stop','FINISHED',50),
 ('CONTROL_ARM','COMPLETE_CONTROL_ARM','طبق کامل','Complete Control Arm','FINISHED',10),
 ('CONTROL_ARM','CONTROL_ARM_BUSHING','بوش طبق','Control Arm Bushing','FINISHED',20),
 ('CONTROL_ARM','CONTROL_ARM_BALL_JOINT','سیبک طبق','Control Arm Ball Joint','FINISHED',30),
 ('REPAIR_KITS','FRONT_SUSPENSION_KIT','کیت جلوبندی','Front Suspension Kit','KIT',10),
 ('REPAIR_KITS','CONTROL_ARM_KIT','کیت طبق','Control Arm Kit','KIT',20),
 ('REPAIR_KITS','STABILIZER_KIT','کیت موجگیر','Stabilizer Kit','KIT',30),
 ('TRADING','RADIATOR_HEATER_HOSE','شلنگ رادیاتور و بخاری','Radiator & Heater Hose','PURCHASED',10),
 ('TRADING','SHOCK_ABSORBER','کمک‌فنر','Shock Absorber','PURCHASED',20),
 ('TRADING','BRAKE_PAD_DISC','لنت و دیسک ترمز','Brake Pad & Disc','PURCHASED',30),
 ('TRADING','SELECTED_TRADING_PART','قطعات بازرگانی منتخب','Selected Trading Part','PURCHASED',40)
) AS x(family_code,code,name_fa,name_en,product_type,sort_order)
ON f.code=x.family_code
ON CONFLICT (code) DO UPDATE SET
 family_id=EXCLUDED.family_id,name_fa=EXCLUDED.name_fa,name_en=EXCLUDED.name_en,
 default_product_type=EXCLUDED.default_product_type,sort_order=EXCLUDED.sort_order,updated_at=now();
