"""核价区间旁挂停用件：完成停止 + 此件不装。

件数突然变少时，先看本区间有没有停用，避免误判成算错。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.llm.engineering_change_analysis_repository import (
    EngineeringChangeAnalysisRepository,
)
from app.schemas.llm.analysis_payload import AnalysisResultLeafPayload, RiskEntry
from app.services.llm.analysis.ops.engineering_change import (
    DISCONTINUE_CHANGE_TYPES,
    build_engineering_change_summary,
)

_SAMPLE_LIMIT = 20
_repo = EngineeringChangeAnalysisRepository()


def _as_object_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def build_period_discontinue(
    db: Session,
    *,
    location: str | None,
    vehicle_model: str | None,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    sample_limit: int = _SAMPLE_LIMIT,
) -> AnalysisResultLeafPayload:
    """按核价问句的基地/项目/账期，取该区间生效的停用件。"""
    rows = _repo.query_rows(
        db,
        location=location,
        vehicle_model=vehicle_model,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        change_types=DISCONTINUE_CHANGE_TYPES,
        limit=5000,
    )
    summary = build_engineering_change_summary(rows, sample_limit=sample_limit)
    discontinue_count = int(str(summary.get("discontinue_count") or 0))
    has_discontinue = discontinue_count > 0
    return {
        "kind": "period_discontinue",
        "subject": "engineering_change",
        "purpose": "解释核价件数为何变少：本区间生效的完成停止与此件不装",
        "has_discontinue": has_discontinue,
        "discontinue_count": discontinue_count,
        "stop_count": int(str(summary.get("stop_count") or 0)),
        "not_install_count": int(str(summary.get("not_install_count") or 0)),
        "stop_items": _as_object_list(summary.get("stop_items")),
        "not_install_items": _as_object_list(summary.get("not_install_items")),
        "effective_periods": _as_object_list(summary.get("effective_periods")),
        "sample_truncated": bool(summary.get("sample_truncated")),
        "message": (
            "本区间有停用件（完成停止/此件不装），核价件数减少可能由此导致，不是算错"
            if has_discontinue
            else "本区间未见完成停止或此件不装"
        ),
    }


def period_discontinue_risk_entry(
    payload: AnalysisResultLeafPayload,
) -> RiskEntry | None:
    if not payload.get("has_discontinue"):
        return None
    samples = _as_object_list(payload.get("stop_items"))[:4]
    samples.extend(_as_object_list(payload.get("not_install_items"))[:4])
    return {
        "risk_type": "period_discontinue",
        "count": int(str(payload.get("discontinue_count") or 0)),
        "message": str(payload.get("message") or "本区间有停用件"),
        "samples": samples,
        "sample_part_numbers": [
            (
                item.get("before_part_number")
                or item.get("after_part_number")
                or item.get("before_assembly_part_number")
                or item.get("after_assembly_part_number")
            )
            for item in samples
            if isinstance(item, dict)
        ],
    }


def should_attach_period_discontinue(
    *,
    analyses: list[str],
    asks_part_price: bool,
    part_number: str | None,
) -> bool:
    """概况/趋势/风险才挂；单件问价不打扰。"""
    if asks_part_price and part_number:
        return False
    return any(kind in analyses for kind in ("summary", "trend", "risk", "comparison"))
