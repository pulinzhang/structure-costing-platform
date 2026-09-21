"""材料清单导入校验：文件、解析结果、项目范围、再导不得出新号。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.common.period import SOP_NEW_NUMBER_REJECT
from app.common.timezone import now
from app.common.upload_scope_validation import validate_bom_material_upload_scope
from app.config import settings
from app.exceptions.base import BusinessException
from app.models.bom import BomNode, BomSnapshot
from app.parsers.bom.models import BomParsedNode
from app.services.bom.bom.rules.internal_number_uniqueness import (
    validate_internal_number_uniqueness,
)
from app.services.bom.bom.rules.l0_seq_validator import (
    format_l0_seq_issues,
    inspect_l0_seq_nos,
    l0_seq_occurrences,
)
from app.services.bom.bom.rules.subassembly_consistency import (
    validate_subassembly_consistency,
)
from app.services.masterdata.vehicle_model.service import VehicleModelService


def require_introducible_project(db: Session, location: str, vehicle_model: str) -> tuple[str, str]:
    clock = now()
    return VehicleModelService().require_introducible(
        db,
        (location or "").strip(),
        (vehicle_model or "").strip(),
        clock.year,
        clock.month,
    )


def validate_upload_file(*, filename: str, file_content: bytes) -> None:
    original_name = Path(filename).name
    ext = Path(original_name).suffix.lower()
    if ext not in {".xlsx", ".xls"}:
        raise BusinessException("仅支持 .xlsx / .xls 文件")
    if not file_content:
        raise BusinessException("文件内容为空")
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        raise BusinessException(f"文件过大，上限 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB")


def require_consecutive_l0_seq_nos(nodes: list[BomParsedNode]) -> None:
    report = inspect_l0_seq_nos(l0_seq_occurrences(nodes))
    message = format_l0_seq_issues(report)
    if message:
        raise BusinessException(message)


def validate_parsed_nodes(nodes: list[BomParsedNode]) -> None:
    if not nodes:
        raise BusinessException("未解析到 BOM 节点，请检查 Excel 格式")
    require_consecutive_l0_seq_nos(nodes)
    validate_internal_number_uniqueness(nodes)
    validate_subassembly_consistency(nodes)


def resolve_upload_scope(
    *,
    location: str,
    selected_vehicle_model: str,
    file_vehicle_model: str | None,
    file_bom_version: str | None,
) -> tuple[str, str, str]:
    scope = validate_bom_material_upload_scope(
        location=location,
        vehicle_model=file_vehicle_model,
        bom_version=file_bom_version,
    )
    VehicleModelService().assert_matches_selected(selected_vehicle_model, scope.vehicle_model)
    return scope.location, selected_vehicle_model, scope.bom_version


def require_l0_part_numbers(nodes: list[BomParsedNode]) -> list[str]:
    numbers = [parsed.part_number for parsed in nodes if parsed.level == 0]
    if not numbers:
        raise BusinessException("未解析到总成（L0）")
    return numbers


def require_matching_snapshot_version(
    existing_heads: list[BomSnapshot], bom_version: str
) -> BomSnapshot:
    matching = [head for head in existing_heads if head.bom_version == bom_version]
    if not matching:
        raise BusinessException(SOP_NEW_NUMBER_REJECT)
    return matching[0]


def require_file_l0_already_on_snapshot(
    file_l0_numbers: list[str], existing_l0: dict[str, BomNode]
) -> None:
    unknown = [number for number in file_l0_numbers if number not in existing_l0]
    if unknown:
        raise BusinessException(SOP_NEW_NUMBER_REJECT)
