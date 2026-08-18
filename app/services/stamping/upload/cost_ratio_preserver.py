"""
上传覆盖时沿用已人工设置的工序成本比率。

在 Excel 解析完成之后、删旧写入之前，用库中已有工序回写解析结果上的 cost_ratio。
查询范围由 Service 通过 Repository 限定（基地 + 冲压工厂 + 车型 + 版本）；
本类只按零件号 + 工序号回写，避免跨范围错位。
"""

from __future__ import annotations

import logging
from decimal import Decimal

from app.common.money import Q2, quantize_money
from app.models.stamping import StampingProcess
from app.parsers.stamping.models.process import Process

logger = logging.getLogger("service.stamping_upload.cost_ratio_preserver")

_DEFAULT_COST_RATIO = Decimal("1.00")


class ProcessCostRatioPreserver:
    """把同一范围内已设的工序成本比率写回解析后的工序列表。"""

    def apply(
        self,
        parsed_processes: list[Process],
        existing_processes: list[StampingProcess],
    ) -> int:
        """按零件号 + 工序号回写 cost_ratio；对不上则保持解析默认 1.00。"""
        if not parsed_processes:
            return 0

        ratio_by_part_seq = _index_by_part_seq(existing_processes)
        preserved = 0
        for process in parsed_processes:
            key = (_norm(process.part_number), _norm(process.process_seq))
            if not key[0] or not key[1]:
                process.cost_ratio = _DEFAULT_COST_RATIO
                continue
            ratio = ratio_by_part_seq.get(key)
            if ratio is None:
                process.cost_ratio = _DEFAULT_COST_RATIO
                continue
            process.cost_ratio = ratio
            preserved += 1

        logger.info(
            "沿用已设工序比率: %d/%d",
            preserved,
            len(parsed_processes),
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


def _norm(value: str | None) -> str:
    return (value or "").strip()


def _as_cost_ratio(value: Decimal | None) -> Decimal:
    if value is None:
        return _DEFAULT_COST_RATIO
    return quantize_money(value, Q2)
