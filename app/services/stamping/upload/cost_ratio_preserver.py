"""
覆盖上传时处理工序 cost_ratio：副产品 0；已有同零件号+工序号沿用；新增走 resolver。

默认比例规则见 docs/stamping/stamping-process-confirmation-design.md §4。
"""

from __future__ import annotations

import logging
from decimal import Decimal

from app.common.money import Q2, quantize_money
from app.models.stamping import StampingProcess
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.services.stamping.upload.cost_ratio_resolver import (
    DEFAULT_COST_RATIO,
    is_prg_family,
    is_shared_first_process_code,
    later_ops_are_blank,
    later_ops_have_shared_die,
    resolve_new_process_cost_ratio,
)

logger = logging.getLogger("service.stamping_upload.cost_ratio_preserver")

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
        processes_by_part = _index_processes_by_part(parsed_processes)
        previous_automation_by_part, previous_first_code_by_part = _previous_excel_neighbors(
            parsed_parts, processes_by_part
        )
        later_shared_by_part = _later_ops_shared_by_part(
            parsed_parts, processes_by_part, previous_first_code_by_part
        )
        preserved = 0
        assigned_new = 0
        for process in parsed_processes:
            key = (_norm(process.part_number), _norm(process.process_seq))
            if not key[0] or not key[1]:
                process.cost_ratio = DEFAULT_COST_RATIO
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
            siblings = processes_by_part.get(key[0], [])
            process.cost_ratio = resolve_new_process_cost_ratio(
                automation=part.automation if part else None,
                process_method=part.process_method if part else None,
                process_code=process.process_code,
                is_first_process=bool(siblings) and process is siblings[0],
                process_count=len(siblings),
                first_process_code=siblings[0].process_code if siblings else None,
                previous_automation=previous_automation_by_part.get(key[0]),
                previous_first_process_code=previous_first_code_by_part.get(key[0]),
                later_ops_are_shared=later_shared_by_part.get(key[0], False),
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


def _index_processes_by_part(parsed_processes: list[Process]) -> dict[str, list[Process]]:
    index: dict[str, list[Process]] = {}
    for process in parsed_processes:
        part_number = _norm(process.part_number)
        if not part_number:
            continue
        index.setdefault(part_number, []).append(process)
    return index


def _previous_excel_neighbors(
    parsed_parts: list[Part],
    processes_by_part: dict[str, list[Process]],
) -> tuple[dict[str, str | None], dict[str, str | None]]:
    """Excel 零件出现顺序上，上一件的自动化列与第一序代码（不按零件号配对）。"""
    previous_automation: str | None = None
    previous_first_code: str | None = None
    automation_by_part: dict[str, str | None] = {}
    first_code_by_part: dict[str, str | None] = {}
    for part in parsed_parts:
        part_number = _norm(part.part_number)
        if not part_number:
            continue
        automation_by_part[part_number] = previous_automation
        first_code_by_part[part_number] = previous_first_code
        previous_automation = part.automation
        siblings = processes_by_part.get(part_number, [])
        previous_first_code = siblings[0].process_code if siblings else None
    return automation_by_part, first_code_by_part


def _later_ops_shared_by_part(
    parsed_parts: list[Part],
    processes_by_part: dict[str, list[Process]],
    previous_first_code_by_part: dict[str, str | None],
) -> dict[str, bool]:
    """
    本件后续含双槽/合并，或右件后序空码，或成对邻件带这些标记。

    第一序为「共用」只看上一件；否则只看下一件。
    仅 PRG 家族成对；一出二后序有代码不算后序共模。
    """
    ordered: list[str] = []
    for part in parsed_parts:
        part_number = _norm(part.part_number)
        if part_number:
            ordered.append(part_number)

    own_later_shared: dict[str, bool] = {}
    is_family: dict[str, bool] = {}
    first_code_by_part: dict[str, str | None] = {}
    for part_number in ordered:
        siblings = processes_by_part.get(part_number, [])
        first_code = siblings[0].process_code if siblings else None
        first_code_by_part[part_number] = first_code
        is_family[part_number] = len(siblings) > 1 and is_prg_family(
            first_code, previous_first_code_by_part.get(part_number)
        )
        later_codes = [process.process_code for process in siblings[1:]]
        own_later_shared[part_number] = later_ops_have_shared_die(later_codes) or (
            is_shared_first_process_code(first_code) and later_ops_are_blank(later_codes)
        )

    mapping: dict[str, bool] = {}
    for index, part_number in enumerate(ordered):
        shared = own_later_shared.get(part_number, False)
        if is_family.get(part_number):
            first_is_shared = is_shared_first_process_code(first_code_by_part.get(part_number))
            if first_is_shared:
                prev_index = index - 1
                if prev_index >= 0:
                    neighbor = ordered[prev_index]
                    if is_family.get(neighbor) and own_later_shared.get(neighbor):
                        shared = True
            else:
                next_index = index + 1
                if next_index < len(ordered):
                    neighbor = ordered[next_index]
                    if is_family.get(neighbor) and own_later_shared.get(neighbor):
                        shared = True
        mapping[part_number] = shared
    return mapping


def _norm(value: str | None) -> str:
    return (value or "").strip()


def _as_cost_ratio(value: Decimal | None) -> Decimal:
    if value is None:
        return DEFAULT_COST_RATIO
    return quantize_money(value, Q2)
