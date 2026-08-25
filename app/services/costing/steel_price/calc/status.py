"""批次状态判定。"""

from __future__ import annotations

from app.exceptions.base import BusinessException
from app.services.costing.steel_price.calc.models import CalcRow, SteelPriceCalcResult
from app.services.costing.steel_price.spec_format import build_spec

# 批次状态（落库 steel_price_calc_logs.status）
STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"

DUPLICATE_PERIOD_CALC_MESSAGE = "当前期别正在计算中，请勿重复提交。"

# processing 超过此时长视为僵死，允许重新提交
STALE_PROCESSING_SECONDS = 2 * 3600


class DuplicatePeriodCalcError(BusinessException):
    """同一年度+月份+基地已有进行中的计算。"""

    def __init__(self, message: str = DUPLICATE_PERIOD_CALC_MESSAGE) -> None:
        super().__init__(message=message, code=409)


def resolve_batch_status(result: SteelPriceCalcResult, rows: list[CalcRow]) -> str:
    if result.failed_count > 0:
        return STATUS_PARTIAL
    if result.material_count == 0:
        return STATUS_FAILED
    if result.enriched_count == 0:
        return STATUS_FAILED
    if result.no_base_count > 0:
        return STATUS_PARTIAL
    if any(r.calc_status != "success" for r in rows):
        return STATUS_PARTIAL
    if result.created_count + result.updated_count == 0 and result.skipped_approved_count == 0:
        return STATUS_FAILED
    return STATUS_SUCCESS


def summarize_match_status(rows: list[CalcRow]) -> dict[str, int]:
    stats: dict[str, int] = {}
    for row in rows:
        stats[row.match_status] = stats.get(row.match_status, 0) + 1
    return dict(sorted(stats.items()))


def summarize_policy_hits(rows: list[CalcRow], *, prefix: str) -> tuple[int, int]:
    """返回 (命中数, 未命中数)，prefix 为 thickness / width。"""
    attr = f"{prefix}_policy_id"
    hit = sum(1 for row in rows if getattr(row, attr, None) is not None)
    return hit, len(rows) - hit


def collect_row_warnings(rows: list[CalcRow], *, keyword: str | None = None) -> list[str]:
    """收集行级警告；keyword 非空时只保留包含该关键字的消息。"""
    warnings: list[str] = []
    for row in rows:
        if not row.messages:
            continue
        messages = row.messages
        if keyword:
            messages = [m for m in messages if keyword in m]
            if not messages:
                continue
        text = "；".join(messages)
        warnings.append(
            f"{row.grade} {build_spec(row.thickness, row.width or 0)} {text}"
        )
    return warnings
