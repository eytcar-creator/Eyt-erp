from pathlib import Path

MIGRATION = Path("migrations/029_eyt_master_product_tree_v1.sql").read_text(encoding="utf-8")

def test_master_product_tree_contains_all_families():
    for code in (
        "STEERING", "FRONT_SUSPENSION", "BUSHINGS", "MOUNTING",
        "BELLOWS_RUBBER", "CONTROL_ARM", "REPAIR_KITS", "TRADING"
    ):
        assert "('" + code + "'" in MIGRATION

def test_capacity_policy_is_not_a_sales_ceiling():
    assert "normal maximum is planning capacity, not a sales ceiling" in MIGRATION
    assert "CUSTOMER_ORDER_OVERRIDE" in MIGRATION
    assert "ABOVE_NORMAL_CAPACITY_REVIEW" in MIGRATION

def test_capacity_minimums():
    for quantities, family in {
        "80000, 120000": "FRONT_SUSPENSION",
        "40000, 80000": "BUSHINGS",
        "10000, 50000": "BELLOWS_RUBBER",
        "5000, 20000": "MOUNTING",
    }.items():
        assert quantities in MIGRATION
        assert family in MIGRATION


def test_canonical_subfamilies_are_seeded():
    migration = Path("migrations/030_eyt_master_product_tree_v1_1.sql").read_text(encoding="utf-8")
    for code in (
        "STEERING_BALL_JOINT", "AXIAL_JOINT", "FRONT_STABILIZER_LINK",
        "REAR_STABILIZER_LINK", "CONTROL_ARM_BALL_JOINT",
        "SMALL_CONTROL_ARM_BUSH", "LARGE_CONTROL_ARM_BUSH",
        "ENGINE_MOUNT", "SHOCK_ABSORBER_MOUNT", "STEERING_BELLOW",
        "AXLE_BELLOW", "SLOTTED_RUBBER", "COMPLETE_CONTROL_ARM",
        "FRONT_SUSPENSION_KIT", "RADIATOR_HEATER_HOSE",
    ):
        assert "'" + code + "'" in migration
