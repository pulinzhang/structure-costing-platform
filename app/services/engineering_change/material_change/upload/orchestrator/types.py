"""材料变更指挥家入参。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.services.engineering_change.material_change.upload.gates import MaterialChangeGatedRow

ProgressCallback = Callable[[int, str], None]


@dataclass(slots=True)
class MaterialChangeExecuteArgs:
    log_id: int
    location: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    file_content: bytes


@dataclass(slots=True)
class MaterialChangePrepared:
    log_id: int
    rows: list[MaterialChangeGatedRow]


@dataclass(slots=True)
class MaterialChangeHistoryLink:
    """管线写入冲压后的一条效果。row_index 对准备好的 Excel 行。"""

    row_index: int
    before_id: int
    after_id: int


@dataclass(slots=True)
class MaterialChangePipeline:
    links: list[MaterialChangeHistoryLink]
