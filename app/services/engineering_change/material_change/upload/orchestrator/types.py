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
