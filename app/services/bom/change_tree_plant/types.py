"""合册种树规格与结果。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BomChangePlantSpec:
    """种树所需工程变更单字段（与 EC ChangeOrderRowParsed 解耦，避免上游依赖 EC）。"""

    change_type: str
    before_assembly_part_number: str
    after_assembly_part_number: str | None
    assembly_name: str | None
    part_level: str
    before_part_number: str | None
    after_part_number: str | None
    part_name: str | None


@dataclass(slots=True)
class BomChangePlantResult:
    new_l0_id: int
    not_install_count: int = 0
