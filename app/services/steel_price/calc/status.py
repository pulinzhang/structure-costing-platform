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
            f"{row.grade} {float(row.thickness):.4f}*{float(row.width or 0):.2f} {text}"
        )
    return warnings
