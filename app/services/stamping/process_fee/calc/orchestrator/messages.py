"""冲压加工费计算过程文案（给人看，不写字段名）。"""

from __future__ import annotations

from typing import Protocol

from app.schemas.vo.stamping_process_fee_vo import (
    StampingProcessFeeCalcResultVO,
    StampingProcessFeeFailedItemVO,
)

_SCRAP_REASON = "废料副产品"


class _BatchResultView(Protocol):
    success_count: int
    zero_fee_count: int
    scrap_zero_count: int
    skipped_approved_count: int
    failed_items: list[StampingProcessFeeFailedItemVO]
    zero_fee_items: list[StampingProcessFeeFailedItemVO]


def format_prep_opening(year: int, location: str, supplier: str) -> str:
    return f"开始计算：{year}年，{location}，{supplier}"


def format_rate_loaded(rate_count: int) -> str:
    return f"已加载 {rate_count} 档冲次单价"


def format_parts_matched(part_count: int) -> str:
    return f"本范围共 {part_count} 个有效期内冲压零件"


def _join_part_numbers(items: list[StampingProcessFeeFailedItemVO], limit: int = 8) -> str:
    numbers = [item.part_number for item in items if item.part_number]
    shown = numbers[:limit]
    text = "、".join(shown)
    extra = len(numbers) - limit
    if extra > 0:
        return f"{text} 等 {len(numbers)} 件"
    return text


def append_result_detail(detail_lines: list[str], batch: _BatchResultView) -> None:
    failed = len(batch.failed_items)
    if failed == 0:
        detail_lines.append(f"{batch.success_count} 个零件都算完了，没有失败。")
    elif batch.success_count:
        detail_lines.append(
            f"算完 {batch.success_count} 个，还有 {failed} 个没算上（原因见下方）。"
        )
    else:
        detail_lines.append(f"{failed} 个都没算上（原因见下方）。")

    if batch.skipped_approved_count:
        detail_lines.append(f"另有 {batch.skipped_approved_count} 件已审核，本次没重算。")

    scrap_count = batch.scrap_zero_count
    other_count = max(0, batch.zero_fee_count - scrap_count)
    if scrap_count:
        detail_lines.append(
            f"其中 {scrap_count} 件是废料副产品（一模多穴带出来的小件），"
            "按规则不计冲压费，不用补其它费用。"
        )
    if other_count:
        other_items = [
            item
            for item in batch.zero_fee_items
            if not (item.reason or "").startswith(_SCRAP_REASON)
        ]
        numbers = _join_part_numbers(other_items) if other_items else ""
        suffix = f"：{numbers}" if numbers else ""
        detail_lines.append(
            f"还有 {other_count} 件冲压费为 0，请到加工费列表核对或补其它费用{suffix}。"
        )


def calc_task_completed_message(result: StampingProcessFeeCalcResultVO) -> str:
    label = "完成" if result.status == "success" else "部分完成"
    other_zero = max(0, result.zero_fee_count - result.scrap_zero_count)
    if result.failed_count and result.success_count:
        return f"计算{label}：成功 {result.success_count} 个，失败 {result.failed_count} 个"
    if result.failed_count and not result.success_count:
        return f"计算失败：{result.failed_count} 个都没算上"
    if other_zero > 0:
        return (
            f"计算{label}：{result.success_count} 个成功，"
            f"{other_zero} 个冲压费为 0，请到列表核对"
        )
    if result.scrap_zero_count:
        return (
            f"计算完成：{result.success_count} 个都成功。"
            f"其中 {result.scrap_zero_count} 件是废料副产品，冲压费记 0，属正常"
        )
    return f"计算完成：{result.success_count} 个都成功"


def calc_task_failed_message(result: StampingProcessFeeCalcResultVO) -> str:
    return f"计算失败：成功 {result.success_count} 个，失败 {result.failed_count} 个"
