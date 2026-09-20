"""核价旁挂：外发采购对象未指定供应商。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.repositories.llm.procurement_object_analysis_repository import ProcurementObjectRow
from app.services.llm.analysis.shared.period_missing_supplier import (
    build_period_missing_supplier,
    period_missing_supplier_risk_entry,
    should_attach_period_missing_supplier,
)


def test_should_attach_period_missing_supplier_for_summary() -> None:
    assert should_attach_period_missing_supplier(
        analyses=["summary"], asks_part_price=False, part_number=None
    )
    assert should_attach_period_missing_supplier(
        analyses=["risk", "trend"], asks_part_price=False, part_number=None
    )


def test_should_skip_period_missing_supplier_for_part_price() -> None:
    assert not should_attach_period_missing_supplier(
        analyses=["drilldown"], asks_part_price=True, part_number="2856"
    )


def test_build_period_missing_supplier_empty() -> None:
    db = MagicMock()
    with patch(
        "app.services.llm.analysis.shared.period_missing_supplier._repo.query_rows",
        return_value=[],
    ):
        payload = build_period_missing_supplier(db, location="芜湖", vehicle_model="T13J")
    assert payload["has_missing_supplier"] is False
    assert payload["missing_supplier_count"] == 0
    assert "未见" in str(payload["message"])
    assert period_missing_supplier_risk_entry(payload) is None


def test_build_period_missing_supplier_with_items() -> None:
    db = MagicMock()
    rows = [
        ProcurementObjectRow(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/00",
            part_number="P-MISS",
            part_name="缺厂家件",
            section="normal",
            object_kind="stamping",
            confirm_status="outsourced",
            audit_status="pending",
            supplier_name=None,
        ),
        ProcurementObjectRow(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/00",
            part_number="P-OK",
            part_name="已指定",
            section="normal",
            object_kind="stamping",
            confirm_status="outsourced",
            audit_status="approved",
            supplier_name="某某厂",
        ),
    ]
    with patch(
        "app.services.llm.analysis.shared.period_missing_supplier._repo.query_rows",
        return_value=rows,
    ):
        payload = build_period_missing_supplier(db, location="芜湖", vehicle_model="T13J")
    assert payload["has_missing_supplier"] is True
    assert payload["missing_supplier_count"] == 1
    assert payload["missing_supplier_items"][0]["part_number"] == "P-MISS"
    risk = period_missing_supplier_risk_entry(payload)
    assert risk is not None
    assert risk["risk_type"] == "period_missing_supplier"
    assert "P-MISS" in (risk.get("sample_part_numbers") or [])
