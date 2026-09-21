"""材料清单写入：建头 / 插节点 / SOP 再导对齐 / 溯源登记。只 flush，不 commit。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.engineering_change_gates import PeriodRoot, is_sop_alignable_root
from app.exceptions.base import BusinessException
from app.models.bom import BomNode, BomSnapshot
from app.parsers.bom.models import BomParsedNode, BomParseResult
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.persist import apply_payload_fields
from app.schemas.dto.bom_dto import BomNodeWrite, BomSnapshotWrite
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.upload.gates.validate import (
    require_file_l0_already_on_snapshot,
    require_matching_snapshot_version,
)
from app.services.file_trace.register import register_existing
from app.services.masterdata.vehicle_model.service import VehicleModelService

# Excel 列号（1-based）：各层级「零件号」列，与 node_parser 一致
_EXCEL_PART_COL_BY_LEVEL = {0: 3, 1: 9, 2: 14}

_ALIGN_SKIP_FIELDS = frozenset(
    {
        "id",
        "snapshot_id",
        "parent_id",
        "level",
        "seq_no",
        "location",
        "vehicle_model",
        "bom_version",
        "effective_year",
        "effective_month",
        "expiry_year",
        "expiry_month",
        "created_by",
        "created_at",
        "parent_index",
        "sketch_bytes",
        "source_row",
    }
)


def flush_bom_upload(
    db: Session,
    *,
    parse_result: BomParseResult,
    location: str,
    vehicle_model: str,
    bom_version: str,
    original_name: str,
    relative_path: str,
    file_hash: str,
    saved_images: dict[int, str],
    file_l0_numbers: list[str],
    current_user: UserVO,
) -> tuple[BomSnapshot, bool]:
    snapshot_repo = BomSnapshotRepository()
    node_repo = BomNodeRepository()
    existing_heads = snapshot_repo.list_by_location_model(db, location, vehicle_model)
    audit = audit_create(current_user)
    effective_year, effective_month, expiry_year, expiry_month = (
        VehicleModelService().project_sop_period(db, location, vehicle_model)
    )
    sheet_name = parse_result.sheet_name
    meta = parse_result.meta

    if not existing_heads:
        snapshot = snapshot_repo.create(
            db,
            BomSnapshotWrite(
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                product_category=meta.product_category,
                customer_name=meta.customer_name,
                stage=meta.stage or "initial",
                doc_no=meta.doc_no,
                prepare_dept=meta.prepare_dept,
                doc_date=meta.doc_date,
                revision_date=meta.revision_date,
                title=meta.title,
                source_filename=original_name,
                source_sheet_name=parse_result.sheet_name,
                source_file_path=relative_path,
                source_file_hash=file_hash,
                status="active",
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        insert_parsed_nodes(
            db,
            node_repo=node_repo,
            snapshot_id=snapshot.id,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            parsed_nodes=parse_result.nodes,
            saved_images=saved_images,
            original_name=original_name,
            sheet_name=sheet_name,
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
            effective_year=effective_year,
            effective_month=effective_month,
            expiry_year=expiry_year,
            expiry_month=expiry_month,
        )
        replaced = False
    else:
        snapshot = require_matching_snapshot_version(existing_heads, bom_version)
        existing_l0 = {row.part_number: row for row in node_repo.list_l0(db, snapshot.id)}
        require_file_l0_already_on_snapshot(file_l0_numbers, existing_l0)
        align_existing_trees(
            db,
            node_repo=node_repo,
            snapshot_id=snapshot.id,
            existing_l0=existing_l0,
            parsed_nodes=parse_result.nodes,
            saved_images=saved_images,
            original_name=original_name,
            sheet_name=sheet_name,
            updated_by=audit["updated_by"],
            sop_year=effective_year,
            sop_month=effective_month,
        )
        snapshot.source_filename = original_name
        snapshot.source_sheet_name = sheet_name
        snapshot.source_file_path = relative_path
        snapshot.source_file_hash = file_hash
        snapshot.updated_by = audit["updated_by"]
        replaced = True

    register_existing(
        db,
        file_category="bom_material",
        stored_relpath=relative_path,
        original_filename=original_name,
        current_user=current_user,
        file_hash=file_hash,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        business_ref_type="bom_snapshot",
        business_ref_id=snapshot.id,
    )
    db.flush()
    return snapshot, replaced


def insert_parsed_nodes(
    db: Session,
    *,
    node_repo: BomNodeRepository | None = None,
    snapshot_id: int,
    location: str,
    vehicle_model: str,
    bom_version: str,
    parsed_nodes: list[BomParsedNode],
    saved_images: dict[int, str],
    original_name: str,
    sheet_name: str | None,
    created_by: str,
    updated_by: str,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    parent_index_to_id: dict[int, int] | None = None,
    indices: list[int] | None = None,
) -> dict[int, int]:
    repo = node_repo or BomNodeRepository()
    index_to_id: dict[int, int] = dict(parent_index_to_id or {})
    order = indices if indices is not None else list(range(len(parsed_nodes)))
    for index in order:
        parsed = parsed_nodes[index]
        parent_id = None
        if parsed.parent_index is not None:
            parent_id = index_to_id.get(parsed.parent_index)
            if parent_id is None:
                raise BusinessException(
                    f"节点父子关系异常: {parsed.part_number} " f"parent_index={parsed.parent_index}"
                )
        row = repo.create(
            db,
            BomNodeWrite(
                snapshot_id=snapshot_id,
                parent_id=parent_id,
                level=parsed.level,
                sort_no=parsed.sort_no,
                seq_no=parsed.seq_no,
                internal_number=parsed.internal_number,
                part_number=parsed.part_number,
                part_name=parsed.part_name,
                qty=parsed.qty,
                qty_unit=parsed.qty_unit or "pcs",
                qty_text=parsed.qty_text,
                node_role=parsed.node_role,
                is_supply_unit=bool(parsed.is_supply_unit),
                material=parsed.material,
                thickness_mm=parsed.thickness_mm,
                thickness_text=parsed.thickness_text,
                material_mill=parsed.material_mill,
                part_weight=parsed.part_weight,
                gauge_developed=parsed.gauge_developed,
                weld_info=parsed.weld_info,
                remark=parsed.remark,
                sketch_url=saved_images.get(index),
                excel_filename=original_name,
                excel_sheet_name=sheet_name,
                excel_row=parsed.source_row,
                excel_part_col=_EXCEL_PART_COL_BY_LEVEL.get(parsed.level),
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                effective_year=effective_year,
                effective_month=effective_month,
                expiry_year=expiry_year,
                expiry_month=expiry_month,
                created_by=created_by,
                updated_by=updated_by,
            ),
        )
        index_to_id[index] = row.id
    return index_to_id


def align_existing_trees(
    db: Session,
    *,
    snapshot_id: int,
    existing_l0: dict[str, BomNode],
    parsed_nodes: list[BomParsedNode],
    saved_images: dict[int, str],
    original_name: str,
    sheet_name: str | None,
    updated_by: str,
    sop_year: int,
    sop_month: int,
    node_repo: BomNodeRepository | None = None,
) -> None:
    repo = node_repo or BomNodeRepository()
    children_of = _parsed_children(parsed_nodes)
    for index, parsed in enumerate(parsed_nodes):
        if parsed.level != 0:
            continue
        root = existing_l0[parsed.part_number]
        if not is_sop_alignable_root(
            PeriodRoot(
                effective_year=root.effective_year,
                effective_month=root.effective_month,
                expiry_year=root.expiry_year,
                expiry_month=root.expiry_month,
            ),
            sop_year=sop_year,
            sop_month=sop_month,
        ):
            continue
        apply_payload_fields(root, parsed, skip=_ALIGN_SKIP_FIELDS)
        root.excel_filename = original_name
        root.excel_sheet_name = sheet_name
        root.excel_row = parsed.source_row
        root.excel_part_col = _EXCEL_PART_COL_BY_LEVEL.get(parsed.level)
        if index in saved_images:
            root.sketch_url = saved_images[index]
        root.updated_by = updated_by
        repo.delete_descendants(db, snapshot_id, root.id)
        descendant_indices = _walk_parsed_descendants(children_of, index)
        if not descendant_indices:
            continue
        insert_parsed_nodes(
            db,
            node_repo=repo,
            snapshot_id=snapshot_id,
            location=root.location,
            vehicle_model=root.vehicle_model,
            bom_version=root.bom_version,
            parsed_nodes=parsed_nodes,
            saved_images=saved_images,
            original_name=original_name,
            sheet_name=sheet_name,
            created_by=updated_by,
            updated_by=updated_by,
            effective_year=root.effective_year,
            effective_month=root.effective_month,
            expiry_year=root.expiry_year,
            expiry_month=root.expiry_month,
            parent_index_to_id={index: root.id},
            indices=descendant_indices,
        )


def _parsed_children(nodes: list[BomParsedNode]) -> dict[int, list[int]]:
    children: dict[int, list[int]] = {}
    for index, parsed in enumerate(nodes):
        if parsed.parent_index is None:
            continue
        children.setdefault(parsed.parent_index, []).append(index)
    return children


def _walk_parsed_descendants(children: dict[int, list[int]], root_index: int) -> list[int]:
    ordered: list[int] = []

    def walk(parent: int) -> None:
        for child in children.get(parent, []):
            ordered.append(child)
            walk(child)

    walk(root_index)
    return ordered
