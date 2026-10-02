"""冲压工艺预备：只做能不能写。禁止插零件、commit。"""

from __future__ import annotations

import logging
import os
import tempfile

from sqlalchemy.orm import Session

from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.parsers.stamping.tailor_weld_parser import parse_tailor_weld_excel
from app.services.stamping.part.upload.gates.validate import (
    require_consecutive_part_seq_nos,
    require_no_duplicate_process_seqs,
    require_ordinary_part_fields,
    require_parsed_scope_headers,
    resolve_stamping_upload_scope,
)
from app.services.stamping.part.upload.materials import canonicalize_materials
from app.services.stamping.part.upload.orchestrator.types import (
    PreparedBundle,
    ProgressCallback,
    StampingUploadExecuteArgs,
    report_progress,
)

logger = logging.getLogger("service.stamping_upload")


def prepare_stamping_upload_run(
    db: Session,
    args: StampingUploadExecuteArgs,
    *,
    on_progress: ProgressCallback | None = None,
) -> PreparedBundle:
    report_progress(on_progress, 5, "正在读取并解析 Excel...")
    with tempfile.NamedTemporaryFile(delete=False, suffix=args.filename) as tmp:
        tmp.write(args.file_content)
        tmp_path = tmp.name
    try:
        parse_result = parse_stamping_excel(tmp_path)
        tailor_result = parse_tailor_weld_excel(tmp_path)
        parsed_vehicle, parsed_supplier = require_parsed_scope_headers(
            parsed_vehicle=parse_result.vehicle_model,
            parsed_supplier=parse_result.stamping_supplier,
        )
        location, vehicle_model, version, stamping_supplier, supplier_names = (
            resolve_stamping_upload_scope(
                db,
                parsed_vehicle=parsed_vehicle,
                parsed_supplier=parsed_supplier,
                parsed_version=parse_result.version,
            )
        )
        require_no_duplicate_process_seqs(parse_result.processes)
        require_consecutive_part_seq_nos(parse_result.parts)
        canonicalize_materials(db, parse_result.parts, tailor_result.assemblies)
        require_ordinary_part_fields(
            parse_result.parts,
            tailor_parent_numbers=set(tailor_result.parent_part_numbers),
        )
        logger.info(
            "解析 Excel 完成：%d 个零件、%d 道工序、%d 个拼焊总成",
            len(parse_result.parts),
            len(parse_result.processes),
            tailor_result.assembly_count,
        )
        report_progress(
            on_progress,
            40,
            f"解析完成：{len(parse_result.parts)} 个零件、"
            f"{len(parse_result.processes)} 道工序、"
            f"{tailor_result.assembly_count} 个拼焊件，正在保存文件...",
        )
        return PreparedBundle(
            filename=args.filename,
            file_content=args.file_content,
            parse_result=parse_result,
            tailor_result=tailor_result,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            stamping_supplier=stamping_supplier,
            supplier_names=supplier_names,
            tailor_parent_numbers=set(tailor_result.parent_part_numbers),
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
