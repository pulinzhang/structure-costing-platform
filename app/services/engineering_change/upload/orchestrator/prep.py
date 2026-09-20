"""
工程变更预备（指挥家第一步）。

职责边界：只做「能不能写」——抽表、变更单校验、定位变更前总成、工艺硬门禁、
一次解析材料清单与项目失效月，装进 PreparedBundle。
禁止：种树、插工艺/布点、commit 业务终态（那是 pipeline / persist 的事）。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import (
    CHANGE_TYPE_STOP,
    EC_AFTER_ASSEMBLY_BUSY,
    EC_CHANGE_ORDER_COLUMNS,
    EC_PROCUREMENT_LIST_REQUIRED_DETAIL,
    EC_PROJECT_MISMATCH,
    quoted,
    require_ec_sheet_versions,
)
from app.common.period import previous_month
from app.exceptions.base import BusinessException
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import parse_bom_excel
from app.parsers.engineering_change.change_order_parser import (
    ChangeOrderRowParsed,
    parse_change_order_sheet,
)
from app.parsers.engineering_change.sheet_extract import (
    SHEET_BOM,
    SHEET_CHANGE_ORDER,
    extract_named_sheets,
)
from app.repositories.engineering_change.upload_log_repository import (
    EngineeringChangeUploadLogRepository,
)
from app.services.bom.bom.engineering import BomEngineeringService
from app.services.bom.procurement_object.service import BomProcurementObjectService
from app.services.engineering_change.upload.gates.bom_slice import slice_bom_nodes_for_l0
from app.services.engineering_change.upload.gates.process_gates import (
    ProcessGateItem,
    parse_process_confirmation,
    validate_process_hard_gates,
)
from app.services.engineering_change.upload.gates.sheet_consistency import (
    validate_workbook_part_numbers,
)
from app.services.engineering_change.upload.gates.tree_gates import (
    apply_process_sketches_to_bom_nodes,
    validate_change_tree_gates,
    validate_identity_gates,
)
from app.services.engineering_change.upload.gates.validate import (
    validate_before_assembly_active,
    validate_bom_l0_matches_change_orders,
    validate_change_order_before_after,
    validate_change_order_rows,
)
from app.services.engineering_change.upload.orchestrator.types import (
    EngineeringChangeExecuteArgs,
    PreparedBundle,
    PreparedChangeOrder,
    ProgressCallback,
    report_progress,
)
from app.services.masterdata.vehicle_model import VehicleModelService


def prepare_engineering_change_run(
    db: Session,
    args: EngineeringChangeExecuteArgs,
    *,
    on_progress: ProgressCallback | None = None,
) -> PreparedBundle:
    log_repo = EngineeringChangeUploadLogRepository()
    bom_service = BomEngineeringService()
    location = args.location
    vehicle_model = args.vehicle_model
    effective_year = args.effective_year
    effective_month = args.effective_month
    location, vehicle_model = VehicleModelService().require_introducible(
        db, location, vehicle_model, effective_year, effective_month
    )

    report_progress(on_progress, 10, "校验工程变更单与抽表")
    sheets = extract_named_sheets(args.file_content)
    change_orders = parse_change_order_sheet(sheets[SHEET_CHANGE_ORDER])
    validate_change_order_rows(
        change_orders,
        page_vehicle_model=vehicle_model,
        page_effective_year=effective_year,
        page_effective_month=effective_month,
    )
    _assert_after_assemblies_idle(
        db,
        change_orders=change_orders,
        location=location,
        vehicle_model=vehicle_model,
        log_id=args.log_id,
        log_repo=log_repo,
    )

    prepared_change_orders: list[PreparedChangeOrder] = []
    customer_name = ""
    snapshot_ids: set[int] = set()
    for change_order in change_orders:
        before_root = _locate_before_root(
            db,
            bom_service=bom_service,
            location=location,
            vehicle_model=vehicle_model,
            change_order=change_order,
            effective_year=effective_year,
            effective_month=effective_month,
        )
        snapshot_ids.add(before_root.snapshot_id)
        snapshot = bom_service.get_snapshot(db, before_root.snapshot_id)
        customer_name = (snapshot.customer_name or "").strip()
        old_nodes = bom_service.list_subtree_nodes(db, root_id=before_root.id)
        after_assembly = None
        if change_order.after_assembly_part_number:
            after_assembly = bom_service.find_l0_by_part_number(
                db,
                location=location,
                vehicle_model=vehicle_model,
                part_number=change_order.after_assembly_part_number,
            )
        after_part_as_l0 = None
        if change_order.after_part_number:
            after_part_as_l0 = bom_service.find_l0_by_part_number(
                db,
                location=location,
                vehicle_model=vehicle_model,
                part_number=change_order.after_part_number,
            )
        validate_change_order_before_after(
            change_order,
            old_nodes=old_nodes,
            after_assembly=after_assembly,
            after_part_as_l0=after_part_as_l0,
        )
        prepared_change_orders.append(
            PreparedChangeOrder(
                change_order=change_order,
                before_root_id=before_root.id,
                before_seq_no=before_root.seq_no,
                snapshot_id=before_root.snapshot_id,
                sliced_bom_nodes=None,
            )
        )

    if len(snapshot_ids) != 1:
        raise BusinessException(
            f"{EC_PROJECT_MISMATCH}。这几行变更前总成不是同一个项目。"
            "请拆成两本，或改成同一个项目后再传。"
        )
    snapshot_id = next(iter(snapshot_ids))
    if BomProcurementObjectService().get_list_id_by_snapshot(db, snapshot_id) is None:
        raise BusinessException(EC_PROCUREMENT_LIST_REQUIRED_DETAIL)

    _, _, project_expiry_year, project_expiry_month = VehicleModelService().project_sop_period(
        db, location, vehicle_model
    )

    parsed_bom = parse_bom_excel(args.file_content, sheet_name=SHEET_BOM)
    file_project = (parsed_bom.meta.vehicle_model or "").strip()
    page_project = vehicle_model.strip()
    if not file_project or file_project.upper() != page_project.upper():
        raise BusinessException(
            f"{EC_PROJECT_MISMATCH}。材料清单第 3 行「项目代号」写成了{quoted(file_project)}，"
            f"上传页是{quoted(page_project)}。请改成同一个项目后再传。"
        )
    parsed_process = parse_process_confirmation(args.file_content)
    process_project = (parsed_process.vehicle_model or "").strip()
    if not process_project or process_project.upper() != page_project.upper():
        raise BusinessException(
            f"{EC_PROJECT_MISMATCH}。冲压工艺确认表标题里的项目写成了{quoted(process_project)}，"
            f"上传页是{quoted(page_project)}。请改确认表标题（写成「{page_project}项目冲压工艺确认表」那种）后再传。"
        )
    node_bom_version = require_ec_sheet_versions(
        bom_version=parsed_bom.meta.bom_version,
        process_version=parsed_process.version,
    )
    process_part_numbers = {
        (part.part_number or "").strip()
        for part in parsed_process.parts
        if (part.part_number or "").strip()
    }
    validate_workbook_part_numbers(
        bom_nodes=parsed_bom.nodes,
        process_part_numbers=process_part_numbers,
        change_orders=change_orders,
    )
    validate_bom_l0_matches_change_orders(parsed_bom.nodes, change_orders)
    apply_process_sketches_to_bom_nodes(parsed_bom.nodes, parsed_process.images_by_part)

    for item in prepared_change_orders:
        if item.change_order.change_type == CHANGE_TYPE_STOP:
            continue
        after_number = item.change_order.after_assembly_part_number
        if not after_number:
            raise BusinessException(
                f"{EC_CHANGE_ORDER_COLUMNS}：工程变更单第 {item.change_order.excel_row} 行"
                f"是{item.change_order.change_type}，必须填变更后总成。"
            )
        item.sliced_bom_nodes = slice_bom_nodes_for_l0(parsed_bom.nodes, after_number)
        old_nodes = bom_service.list_subtree_nodes(db, root_id=item.before_root_id)
        validate_change_tree_gates(item.change_order, old_nodes, item.sliced_bom_nodes)
        validate_identity_gates(old_nodes, item.sliced_bom_nodes)

    report_progress(on_progress, 20, "校验工艺门禁")
    revise_old_to_new = validate_process_hard_gates(
        db,
        items=[
            ProcessGateItem(
                change_order=item.change_order,
                before_root_id=item.before_root_id,
                sliced_nodes=item.sliced_bom_nodes,
            )
            for item in prepared_change_orders
        ],
        process_part_numbers=process_part_numbers,
        location=location,
        vehicle_model=vehicle_model,
        effective_year=effective_year,
        effective_month=effective_month,
        bom_service=bom_service,
    )
    part_change_order_index = _part_change_order_index(prepared_change_orders)

    return PreparedBundle(
        log_id=args.log_id,
        upload_file_id=args.upload_file_id,
        location=location,
        vehicle_model=vehicle_model,
        customer_name=customer_name,
        effective_year=effective_year,
        effective_month=effective_month,
        change_orders=prepared_change_orders,
        file_content=args.file_content,
        project_expiry_year=project_expiry_year,
        project_expiry_month=project_expiry_month,
        node_bom_version=node_bom_version,
        revise_old_to_new=revise_old_to_new,
        part_change_order_index=part_change_order_index,
    )


def _assert_after_assemblies_idle(
    db: Session,
    *,
    change_orders: list[ChangeOrderRowParsed],
    location: str,
    vehicle_model: str,
    log_id: int,
    log_repo: EngineeringChangeUploadLogRepository,
) -> None:
    for change_order in change_orders:
        if not change_order.after_assembly_part_number:
            continue
        busy = [
            row
            for row in log_repo.list_busy_after_assembly(
                db,
                location=location,
                vehicle_model=vehicle_model,
                after_assembly_part_number=change_order.after_assembly_part_number,
            )
            if row.id != log_id
        ]
        if busy:
            raise BusinessException(
                f"{EC_AFTER_ASSEMBLY_BUSY}：{quoted(change_order.after_assembly_part_number)} "
                "已有正在导入的任务。",
                code=409,
            )


def _locate_before_root(
    db: Session,
    *,
    bom_service: BomEngineeringService,
    location: str,
    vehicle_model: str,
    change_order: ChangeOrderRowParsed,
    effective_year: int,
    effective_month: int,
) -> BomNode:
    before_root = bom_service.find_active_l0_by_part_number(
        db,
        location=location,
        vehicle_model=vehicle_model,
        part_number=change_order.before_assembly_part_number,
        as_of_year=effective_year,
        as_of_month=effective_month,
    )
    if before_root is None:
        prev_year, prev_month = previous_month(effective_year, effective_month)
        before_root = bom_service.find_active_l0_by_part_number(
            db,
            location=location,
            vehicle_model=vehicle_model,
            part_number=change_order.before_assembly_part_number,
            as_of_year=prev_year,
            as_of_month=prev_month,
        )
    return validate_before_assembly_active(
        before_root,
        effective_year=effective_year,
        effective_month=effective_month,
        part_number=change_order.before_assembly_part_number,
    )


def _part_change_order_index(change_orders: list[PreparedChangeOrder]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, item in enumerate(change_orders):
        change_order = item.change_order
        if change_order.after_part_number:
            mapping[change_order.after_part_number.strip()] = index
        if change_order.after_assembly_part_number:
            mapping[change_order.after_assembly_part_number.strip()] = index
        if item.sliced_bom_nodes:
            for node in item.sliced_bom_nodes:
                number = (node.part_number or "").strip()
                if number:
                    mapping.setdefault(number, index)
    return mapping
