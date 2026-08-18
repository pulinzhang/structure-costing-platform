"""零件主表字段快照到加工费结果行。"""

from __future__ import annotations

from app.models.stamping import StampingPart
from app.schemas.dto.stamping_process_fee_dto import ProcessFeePartSnapshot


def part_snapshot(part: StampingPart) -> ProcessFeePartSnapshot:
    """从零件主表快照业务字段到加工费结果行。"""
    return ProcessFeePartSnapshot(
        source_part_id=part.id,
        seq_no=part.seq_no,
        part_number=part.part_number,
        part_name=part.part_name,
        material=part.material,
        thickness=part.thickness,
        part_weight=part.part_weight,
        sheet_length=part.sheet_length,
        sheet_width=part.sheet_width,
        parts_per_sheet=part.parts_per_sheet,
        sheet_type=part.sheet_type,
        die_type=part.die_type,
        process_method=part.process_method,
        automation=part.automation,
        part_remark=part.remark,
        sketch_url=part.sketch_url,
        excel_filename=part.excel_filename,
    )
