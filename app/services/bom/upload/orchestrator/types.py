"""材料清单导入编排上下文。"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.bom import BomSnapshot
from app.parsers.bom.models import BomParseResult
from app.services.async_task.worker_runner import ProgressCallback

__all__ = [
    "BomUploadExecuteArgs",
    "PipelineBundle",
    "PreparedBundle",
    "ProgressCallback",
    "report_progress",
]


@dataclass(slots=True)
class BomUploadExecuteArgs:
    file_content: bytes
    filename: str
    location: str
    vehicle_model: str


@dataclass(slots=True)
class PreparedBundle:
    location: str
    vehicle_model: str
    bom_version: str
    original_name: str
    parse_result: BomParseResult
    file_hash: str
    file_content: bytes
    file_l0_numbers: list[str]


@dataclass(slots=True)
class PipelineBundle:
    relative_path: str
    saved_images: dict[int, str]
    snapshot: BomSnapshot
    replaced: bool


def report_progress(on_progress: ProgressCallback | None, progress: int, message: str) -> None:
    if on_progress is not None:
        on_progress(progress, message)
