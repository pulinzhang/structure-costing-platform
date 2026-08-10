"""批次状态判定。"""

from __future__ import annotations

from app.services.steel_price.calc.models import CalcRow, SteelPriceCalcResult


def resolve_batch_status(result: SteelPriceCalcResult, rows: list[CalcRow]) -> str:
    if result.failed_count > 0:
        return "partial"
    if result.material_count == 0:
        return "failed"
    if result.enriched_count == 0:
        return "failed"
    if result.no_base_count > 0:
        return "partial"
    if any(r.calc_status != "success" for r in rows):
        return "partial"
    if result.created_count + result.updated_count == 0 and result.skipped_approved_count == 0:
        return "failed"
    return "success"


def summarize_match_status(rows: list[CalcRow]) -> dict[str, int]:
    stats: dict[str, int] = {}
    for row in rows:
        stats[row.match_status] = stats.get(row.match_status, 0) + 1
    return dict(sorted(stats.items()))
