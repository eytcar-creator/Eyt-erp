from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_profit_first_summary_requires_finance_read():
    source = (ROOT / "api/production/profit_dashboard_api.py").read_text(encoding="utf-8")
    assert "from fastapi import APIRouter, Depends, HTTPException, Query" in source
    assert "from .auth import require_permission" in source
    assert 'def summary(days: int = Query(30, ge=1, le=3650), _=Depends(require_permission("finance.read"))):' in source


def test_profit_first_orders_requires_finance_read():
    source = (ROOT / "api/production/profit_dashboard_api.py").read_text(encoding="utf-8")
    assert 'def orders(days: int = Query(30, ge=1, le=3650), limit: int = Query(200, ge=1, le=1000), _=Depends(require_permission("finance.read"))):' in source
