"""核价区间旁挂：外发采购对象未指定供应商。

设变加件后常忘指定厂家；问核价概况时必须提醒并列零件号。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.llm.procurement_object_analysis_repository import (
    ProcurementObjectAnalysisRepository,
)
from app.schemas.llm.analysis_payload import AnalysisResultLeafPayload, RiskEntry
from app.services.llm.analysis.ops.masterdata import build_procurement_object_summary

_SAMPLE_LIMIT = 20
_repo = ProcurementObjectAnalysisRepository()


def _as_object_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def build_period_missing_supplier(
    db: Session,
    *,
    location: str | None,
    vehicle_model: str | None,
    sample_limit: int = _SAMPLE_LIMIT,
) -> AnalysisResultLeafPayload:
    """按核价问句的基地/项目取采购对象缺供应商清单（清单不按年裁）。"""
    rows = _repo.query_rows(
        db,
        location=location,
        vehicle_model=vehicle_model,
        limit=5000,
    )
    summary = build_procurement_object_summary(rows, sample_limit=sample_limit)
    missing_count = int(str(summary.get("missing_supplier_count") or 0))
    has_missing = missing_count > 0
    items = _as_object_list(summary.get("missing_supplier_items"))
    return {
        "kind": "period_missing_supplier",
        "subject": "procurement_object",
        "purpose": "问核价时提醒：已确认外发但未指定供应商的采购对象",
        "has_missing_supplier": has_missing,
        "missing_supplier_count": missing_count,
        "missing_supplier_items": items,
        "missing_supplier_truncated": bool(summary.get("missing_supplier_truncated")),
        "message": (
            "有外发采购对象未指定供应商，签协议采购对象视图时筛不出，请尽快补厂家"
            if has_missing
            else "未见外发缺供应商"
        ),
    }


def period_missing_supplier_risk_entry(
    payload: AnalysisResultLeafPayload,
) -> RiskEntry | None:
    if not payload.get("has_missing_supplier"):
        return None
    items = _as_object_list(payload.get("missing_supplier_items"))
    return {
        "risk_type": "period_missing_supplier",
        "count": int(str(payload.get("missing_supplier_count") or 0)),
        "message": str(payload.get("message") or "有外发未指定供应商"),
        "missing_supplier_items": items,
        "sample_part_numbers": [
            item.get("part_number") for item in items[:8] if isinstance(item, dict)
        ],
        "truncated": bool(payload.get("missing_supplier_truncated")),
    }


def should_attach_period_missing_supplier(
    *,
    analyses: list[str],
    asks_part_price: bool,
    part_number: str | None,
) -> bool:
    """概况/趋势/风险/对比才挂；单件问价不打扰。"""
    if asks_part_price and part_number:
        return False
    return any(kind in analyses for kind in ("summary", "trend", "risk", "comparison"))
