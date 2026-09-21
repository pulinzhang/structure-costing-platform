"""材料清单预备：只做能不能写。禁止种树、commit。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from app.parsers.bom.bom_parser import parse_bom_excel
from app.services.bom.bom.upload.gates.validate import (
    require_introducible_project,
    require_l0_part_numbers,
    resolve_upload_scope,
    validate_parsed_nodes,
)
from app.services.bom.bom.upload.orchestrator.types import (
    BomUploadExecuteArgs,
    PreparedBundle,
    ProgressCallback,
    report_progress,
)


def prepare_bom_upload_run(
    db: Session,
    args: BomUploadExecuteArgs,
    *,
    on_progress: ProgressCallback | None = None,
) -> PreparedBundle:
    report_progress(on_progress, 10, "校验项目")
    location, selected = require_introducible_project(db, args.location, args.vehicle_model)
    report_progress(on_progress, 25, "正在解析 Excel...")
    parse_result = parse_bom_excel(args.file_content)
    validate_parsed_nodes(parse_result.nodes)
    file_l0_numbers = require_l0_part_numbers(parse_result.nodes)
    location, vehicle_model, bom_version = resolve_upload_scope(
        location=location,
        selected_vehicle_model=selected,
        file_vehicle_model=parse_result.meta.vehicle_model,
        file_bom_version=parse_result.meta.bom_version,
    )
    return PreparedBundle(
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        original_name=Path(args.filename).name,
        parse_result=parse_result,
        file_hash=hashlib.sha256(args.file_content).hexdigest(),
        file_content=args.file_content,
        file_l0_numbers=file_l0_numbers,
    )
