"""无明确时间时，钉到核价表最新年月。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.llm.cost_analysis_repository import L0CostAnalysisRepository
from app.schemas.llm.analysis_query import TimeRange
from app.services.llm._money import month_key
from app.services.llm.query.parser.part_price import is_drilldown_focused
from app.services.llm.query.time_range import asks_latest_costing, question_has_explicit_time


def should_pin_table_latest(question: str, part_number: str | None) -> bool:
    if question_has_explicit_time(question):
        return False
    if asks_latest_costing(question):
        return True
    return bool(part_number) and is_drilldown_focused(question, part_number)


def pin_table_latest_month(
    db: Session,
    *,
    cost_repo: L0CostAnalysisRepository,
    filters: dict[str, str],
    time_range: TimeRange,
) -> tuple[TimeRange, dict[str, str], str | None]:
    try:
        scope = cost_repo.query_latest_card_scope(
            db,
            part_number=filters.get("part_number"),
            location=filters.get("location"),
            vehicle_model=filters.get("vehicle_model"),
        )
        if scope is None and filters.get("part_number"):
            scope = cost_repo.query_latest_card_scope(
                db,
                part_number=None,
                location=filters.get("location"),
                vehicle_model=filters.get("vehicle_model"),
            )
    except (TypeError, ValueError, AttributeError):
        scope = None
    if scope is None:
        return time_range, filters, "核价表暂无可用年月，仍按当前查询窗口取数"
    key = month_key(scope.year, scope.month)
    pinned = TimeRange(start=key, end=key)
    merged = dict(filters)
    if not merged.get("location") and scope.location:
        merged["location"] = scope.location
    if not merged.get("vehicle_model") and scope.vehicle_model:
        merged["vehicle_model"] = scope.vehicle_model
    if not merged.get("bom_version") and scope.bom_version:
        merged["bom_version"] = scope.bom_version
    message = f"按核价表最新年月 {scope.year}年{scope.month:02d}月 取数"
    return pinned, merged, message
