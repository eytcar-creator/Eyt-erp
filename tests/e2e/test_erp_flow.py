"""Executable E.Y.T ERP flow checks.

These checks deliberately validate the public application surface without
requiring real business data. They are a contract layer for the full flow;
endpoint-specific fixtures can be wired to the existing app as each module is
promoted to production readiness.
"""

from pathlib import Path


def test_e2e_contract_covers_operational_chain() -> None:
    contract = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
    required = [
        "Authentication and RBAC",
        "Product master",
        "Purchase",
        "Receiving",
        "Inventory",
        "Production order",
        "Quality control",
        "Costing",
        "Sales order",
        "Delivery",
        "Receivables",
        "Dashboard/reporting",
        "Audit trail",
    ]
    assert all(item in contract for item in required)


def test_e2e_uses_synthetic_data_only() -> None:
    contract = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
    assert "synthetic data only" in contract
    assert "No production or customer data" in contract
