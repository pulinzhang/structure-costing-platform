"""
工序吨位解析。

缺吨位（含 Excel 空格被写成 0）且判定为合并/双槽共模件时，
继承上一零件(id-1)对应工序吨位；
若上一件对应工序为摆剪（无冲压吨位），则本工序同样按摆剪计 0。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.stamping import StampingPart, StampingProcess
from app.repositories.stamping.stamping_repository import StampingPartRepository
from app.services.stamping.process_fee.calc.constants import (
    TONNAGE_SOURCE_INHERITED,
    TONNAGE_SOURCE_SELF,
    TONNAGE_SOURCE_SWING_SHEAR,
)
from app.services.stamping.process_fee.calc.labels import (
    can_inherit_previous_tonnage,
    format_merge_signal_label,
    format_process_label,
    is_swing_shear_process,
    match_previous_process,
    self_tonnage,
    summarize_processes,
)
from app.services.stamping.process_fee.calc.models import ProcessTonnageResolveResult

logger = logging.getLogger("service.stamping.process_fee.calc")


class TonnageResolver:
    """解析单道工序有效吨位（自有 / 共模继承 / 摆剪）。"""

    def __init__(self, part_repo: StampingPartRepository | None = None) -> None:
        self.part_repo = part_repo or StampingPartRepository()

    def get_previous_part(
        self,
        db: Session,
        part: StampingPart,
        prev_part_cache: dict[int, StampingPart | None],
    ) -> StampingPart | None:
        """Excel 导入顺序下，上一零件为 id-1。"""
        if part.id is None or part.id <= 1:
            return None
        prev_id = part.id - 1
        if prev_id not in prev_part_cache:
            prev_part_cache[prev_id] = self.part_repo.get_by_id(db, prev_id)
        return prev_part_cache[prev_id]

    def resolve(
        self,
        db: Session,
        part: StampingPart,
        process: StampingProcess,
        prev_part_cache: dict[int, StampingPart | None],
    ) -> ProcessTonnageResolveResult | str:
        """
        成功返回 ProcessTonnageResolveResult；失败返回原因字符串。
        """
        own_tonnage = self_tonnage(process)
        if own_tonnage is not None:
            return ProcessTonnageResolveResult(
                tonnage=own_tonnage,
                source=TONNAGE_SOURCE_SELF,
            )

        process_label = format_process_label(process)
        method_label = format_merge_signal_label(part, process)
        if not can_inherit_previous_tonnage(part, process):
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"工艺方法/工序「{method_label}」不可继承上一件吨位"
            )

        previous_part = self.get_previous_part(db, part, prev_part_cache)
        if previous_part is None:
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"共模标记「{method_label}」应继承上一件，"
                f"但找不到上一零件(id-1)"
            )

        current_location = (part.location or "").strip()
        previous_location = (previous_part.location or "").strip()
        if not current_location or current_location != previous_location:
            prev_no = previous_part.part_number or str(previous_part.id)
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"共模标记「{method_label}」应继承上一件，"
                f"但基地不一致（当前「{current_location or '(空)'}」，"
                f"上一件 {prev_no} 为「{previous_location or '(空)'}」），不可继承"
            )

        previous_processes = list(previous_part.processes or [])
        prev_summary = summarize_processes(previous_processes)
        prev_no = previous_part.part_number or str(previous_part.id)
        matched = match_previous_process(process, previous_processes)
        if matched is None:
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"共模标记「{method_label}」应继承上一件 "
                f"{prev_no}(id={previous_part.id})，"
                f"但未匹配到对应工序。"
                f"上一件工序清单：{prev_summary}"
            )

        if is_swing_shear_process(matched):
            logger.info(
                "共模件继承摆剪(计0): part=%s method=%s process=%s " "from_part=%s from_process=%s",
                part.part_number,
                method_label,
                process_label,
                previous_part.part_number,
                format_process_label(matched),
            )
            return ProcessTonnageResolveResult(
                tonnage=None,
                source=TONNAGE_SOURCE_SWING_SHEAR,
                inherited_from_part_id=previous_part.id,
                inherited_from_part_number=previous_part.part_number,
                inherited_from_process_seq=matched.process_seq,
                inherited_from_process_code=matched.process_code,
            )

        inherited_tonnage = self_tonnage(matched)
        if inherited_tonnage is None:
            matched_label = format_process_label(matched)
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"共模标记「{method_label}」已匹配上一件 "
                f"{prev_no}(id={previous_part.id}) 工序 {matched_label}，"
                f"但该工序吨位为空。"
                f"上一件工序清单：{prev_summary}"
            )

        logger.info(
            "共模件继承吨位: part=%s location=%s method=%s process=%s "
            "from_part=%s from_process=%s tonnage=%s",
            part.part_number,
            current_location,
            method_label,
            process_label,
            previous_part.part_number,
            format_process_label(matched),
            inherited_tonnage,
        )
        return ProcessTonnageResolveResult(
            tonnage=inherited_tonnage,
            source=TONNAGE_SOURCE_INHERITED,
            inherited_from_part_id=previous_part.id,
            inherited_from_part_number=previous_part.part_number,
            inherited_from_process_seq=matched.process_seq,
            inherited_from_process_code=matched.process_code,
        )
