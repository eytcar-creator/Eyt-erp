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
