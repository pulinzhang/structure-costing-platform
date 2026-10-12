"""批次状态判定。"""

from __future__ import annotations

from typing import TypedDict

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


class ThicknessOutcomeSummary(TypedDict):
    hit: int
    skip: int
    miss: int
    skip_mills: list[str]


def summarize_thickness_outcomes(rows: list[CalcRow]) -> ThicknessOutcomeSummary:
    """厚度命中 / 该厂无厚度块（按基价） / 真实未命中。"""
    hit = 0
    skip = 0
    miss = 0
    skip_mills: set[str] = set()
    for row in rows:
        if row.thickness_policy_id is not None:
            hit += 1
            continue
        if not row.thickness_applicable:
            skip += 1
            mill = (row.steel_mill or "").strip()
            if mill:
                skip_mills.add(mill)
            continue
        miss += 1
    return {
        "hit": hit,
        "skip": skip,
        "miss": miss,
        "skip_mills": sorted(skip_mills),
    }


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
        mill = (row.steel_mill or "").strip() or "-"
        category = (row.category_name or "").strip() or "-"
        spec = build_spec(row.thickness, row.width or 0)
        warnings.append(f"{mill} · {category} · {row.grade} {spec} {text}")
    return warnings
