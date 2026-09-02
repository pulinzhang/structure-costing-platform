"""
覆盖上传时处理工序成本比率。

在 Excel 解析完成之后、删旧写入之前：
- 废料副产品 → 一律 0，不沿用库中值、不走双槽/合并关键字
- 其余：库中已有同零件号+工序号 → 沿用已设 cost_ratio
- 对不上（本次新增）→ 按自动化/工艺方法叠乘默认（双槽/合并/一出二 0.50，级进模 0.80）
"""

from __future__ import annotations

import logging
from decimal import Decimal

from app.common.money import Q2, quantize_money
from app.models.stamping import StampingProcess
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.services.stamping.upload.cost_ratio_resolver import resolve_cost_ratio

logger = logging.getLogger("service.stamping_upload.cost_ratio_preserver")

_DEFAULT_COST_RATIO = Decimal("1.00")
_SCRAP_BYPRODUCT_COST_RATIO = Decimal("0.00")


class ProcessCostRatioPreserver:
    """回写已设比率；新增工序再按工艺方法/自动化赋默认值。"""

    def apply(
        self,
        parsed_processes: list[Process],
        existing_processes: list[StampingProcess],
        parsed_parts: list[Part],
    ) -> int:
        """
        按零件号 + 工序号回写 cost_ratio。

        Returns:
            沿用已设比率的工序数。
        """
        if not parsed_processes:
            return 0

        ratio_by_part_seq = _index_by_part_seq(existing_processes)
        part_by_number = _index_parts(parsed_parts)
        preserved = 0
        assigned_new = 0
        for process in parsed_processes:
            key = (_norm(process.part_number), _norm(process.process_seq))
            if not key[0] or not key[1]:
                process.cost_ratio = _DEFAULT_COST_RATIO
                continue
            part = part_by_number.get(key[0])
            if part is not None and part.is_scrap_byproduct:
                process.cost_ratio = _SCRAP_BYPRODUCT_COST_RATIO
                assigned_new += 1
                continue
            ratio = ratio_by_part_seq.get(key)
            if ratio is not None:
                process.cost_ratio = ratio
                preserved += 1
                continue
            process.cost_ratio = resolve_cost_ratio(
                part.automation if part else None,
                part.process_method if part else None,
            )
            assigned_new += 1

        logger.info(
            "沿用已设工序比率: %d/%d；新增赋默认比率: %d",
            preserved,
            len(parsed_processes),
            assigned_new,
        )
        return preserved


def _index_by_part_seq(
    existing_processes: list[StampingProcess],
) -> dict[tuple[str, str], Decimal]:
    index: dict[tuple[str, str], Decimal] = {}
    for process in existing_processes:
        part = process.part
        part_number = _norm(part.part_number if part is not None else None)
        process_seq = _norm(process.process_seq)
        if not part_number or not process_seq:
            continue
        index[(part_number, process_seq)] = _as_cost_ratio(process.cost_ratio)
    return index


def _index_parts(parsed_parts: list[Part]) -> dict[str, Part]:
    index: dict[str, Part] = {}
    for part in parsed_parts:
        part_number = _norm(part.part_number)
        if not part_number:
            continue
        index[part_number] = part
    return index


def _norm(value: str | None) -> str:
    return (value or "").strip()


def _as_cost_ratio(value: Decimal | None) -> Decimal:
    if value is None:
        return _DEFAULT_COST_RATIO
    return quantize_money(value, Q2)
