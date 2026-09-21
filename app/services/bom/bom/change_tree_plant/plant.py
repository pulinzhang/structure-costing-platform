"""从旧树带走未改零件 + 工程变更变化行种新树。失效由调用方负责。只 flush。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    EC_ADD_ALREADY_ON_TREE,
    EC_BOM_NEW_ROOT,
    EC_NOT_INSTALL_SIGNAL,
    EC_QTY_CHANGED,
    NOT_INSTALL_REMARK,
    is_not_install_row,
    require_bom_header_version,
)
from app.exceptions.base import BusinessException
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import BomParsedNode
from app.schemas.dto.bom_dto import BomNodeWrite
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.change_tree_plant.copy import (
    copied_child_fields,
    excel_row_for_added_part,
    internal_from_file,
)
from app.services.bom.bom.change_tree_plant.number_map import build_number_map
from app.services.bom.bom.change_tree_plant.sketches import copied_sketch_url
from app.services.bom.bom.change_tree_plant.types import BomChangePlantResult, BomChangePlantSpec

if TYPE_CHECKING:
    from app.services.bom.bom.engineering import BomEngineeringService

_EXCEL_PART_COL_BY_LEVEL = {0: 3, 1: 9, 2: 14}


@dataclass(slots=True)
class _PlantSession:
    bom_service: BomEngineeringService
    db: Session
    snapshot_id: int
    location: str
    vehicle_model: str
    bom_version: str
    effective_year: int
    effective_month: int
    expiry_year: int | None
    expiry_month: int | None
    created_by: str
    updated_by: str


def plant_change_tree(
    bom_service: BomEngineeringService,
    db: Session,
    *,
    snapshot_id: int,
    location: str,
    vehicle_model: str,
    before_l0_id: int,
    seq_no: int | None,
    spec: BomChangePlantSpec,
    parsed_nodes: list[BomParsedNode],
    extra_specs: Sequence[BomChangePlantSpec] = (),
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    current_user: UserVO,
    node_bom_version: str | None = None,
) -> BomChangePlantResult:
    bom_version = require_bom_header_version(node_bom_version)
    audit = audit_create(current_user)
    session = _PlantSession(
        bom_service=bom_service,
        db=db,
        snapshot_id=snapshot_id,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        created_by=audit["created_by"],
        updated_by=audit["updated_by"],
    )
    old_nodes = bom_service.list_subtree_nodes(db, root_id=before_l0_id)
    old_by_id = {node.id: node for node in old_nodes}
    old_children: dict[int | None, list[BomNode]] = {}
    for node in old_nodes:
        old_children.setdefault(node.parent_id, []).append(node)

    file_l0_nodes = [node for node in parsed_nodes if node.level == 0]
    if len(file_l0_nodes) != 1:
        raise BusinessException(EC_BOM_NEW_ROOT)
    file_l0 = file_l0_nodes[0]
    if file_l0.part_number != spec.after_assembly_part_number:
        raise BusinessException(EC_BOM_NEW_ROOT)

    all_specs = (spec, *extra_specs)
    has_add_part = any(item.change_type == CHANGE_TYPE_ADD_PART for item in all_specs)
    has_not_install = any(item.change_type == CHANGE_TYPE_NOT_INSTALL for item in all_specs)
    number_map = build_number_map(spec, old_nodes, parsed_nodes, extra_specs)
    file_by_deepest = {node.part_number: node for node in parsed_nodes if node.level != 0}
    _assert_add_and_not_install(all_specs, old_nodes, file_by_deepest)

    old_l0 = old_by_id[before_l0_id]
    new_l0_id = _insert_l0(
        session,
        spec=spec,
        old_l0=old_l0,
        file_l0=file_l0,
        seq_no=seq_no,
    )
    id_remap = {old_l0.id: new_l0_id}
    not_install_count = _copy_old_children(
        session,
        old_l0=old_l0,
        old_children=old_children,
        number_map=number_map,
        file_by_deepest=file_by_deepest,
        has_add_part=has_add_part,
        new_l0_id=new_l0_id,
        id_remap=id_remap,
    )
    _insert_added_parts(
        session,
        all_specs=all_specs,
        parsed_nodes=parsed_nodes,
        file_by_deepest=file_by_deepest,
        number_map=number_map,
        new_l0_id=new_l0_id,
        id_remap=id_remap,
    )
    new_tree = bom_service.list_subtree_nodes(db, root_id=new_l0_id)
    if len(new_tree) <= 1 and not has_add_part and has_not_install:
        raise BusinessException(EC_NOT_INSTALL_SIGNAL)
    return BomChangePlantResult(
        new_l0_id=new_l0_id,
        not_install_count=not_install_count,
        source_id_remap=dict(id_remap),
    )


def _assert_add_and_not_install(
    all_specs: Sequence[BomChangePlantSpec],
    old_nodes: list[BomNode],
    file_by_deepest: dict[str, BomParsedNode],
) -> None:
    old_numbers = {(node.part_number or "").strip() for node in old_nodes}
    for item in all_specs:
        if (
            item.change_type == CHANGE_TYPE_ADD_PART
            and item.after_part_number
            and item.after_part_number.strip() in old_numbers
        ):
            raise BusinessException(EC_ADD_ALREADY_ON_TREE)
        if item.change_type == CHANGE_TYPE_NOT_INSTALL and item.before_part_number:
            marked = file_by_deepest.get(item.before_part_number.strip())
            if marked is None or not is_not_install_row(marked.qty, marked.remark):
                raise BusinessException(EC_NOT_INSTALL_SIGNAL)


def _insert_l0(
    session: _PlantSession,
    *,
    spec: BomChangePlantSpec,
    old_l0: BomNode,
    file_l0: BomParsedNode,
    seq_no: int | None,
) -> int:
    new_l0_number = spec.after_assembly_part_number
    if not new_l0_number:
        raise BusinessException(EC_BOM_NEW_ROOT)
    return _insert_node(
        session,
        parent_id=None,
        level=0,
        part_number=new_l0_number,
        part_name=spec.assembly_name or old_l0.part_name,
        qty=old_l0.qty,
        qty_unit=old_l0.qty_unit,
        qty_text=old_l0.qty_text,
        node_role=old_l0.node_role,
        is_supply_unit=old_l0.is_supply_unit,
        material=old_l0.material,
        thickness_mm=old_l0.thickness_mm,
        thickness_text=old_l0.thickness_text,
        material_mill=old_l0.material_mill,
        part_weight=old_l0.part_weight,
        gauge_developed=old_l0.gauge_developed,
        weld_info=old_l0.weld_info,
        remark=old_l0.remark,
        internal_number=internal_from_file(file_l0, old_l0.internal_number),
        sort_no=old_l0.sort_no or 0,
        seq_no=seq_no,
        excel_row=old_l0.excel_row,
        excel_filename=old_l0.excel_filename,
        excel_sheet_name=old_l0.excel_sheet_name,
        excel_part_col=old_l0.excel_part_col,
        sketch_url=copied_sketch_url(
            location=session.location,
            vehicle_model=session.vehicle_model,
            bom_version=session.bom_version,
            part_number=new_l0_number,
            file_row=file_l0,
            old_sketch_url=None,
            copy_old_sketch=False,
        ),
    )


def _copy_old_children(
    session: _PlantSession,
    *,
    old_l0: BomNode,
    old_children: dict[int | None, list[BomNode]],
    number_map: dict[str, str | None],
    file_by_deepest: dict[str, BomParsedNode],
    has_add_part: bool,
    new_l0_id: int,
    id_remap: dict[int, int],
) -> int:
    not_install_count = 0
    stack = list(old_children.get(old_l0.id, []))
    while stack:
        old_node = stack.pop(0)
        new_number = number_map.get(old_node.part_number, old_node.part_number)
        if new_number is None:
            not_install_count += 1
            continue
        file_row = file_by_deepest.get(new_number) or file_by_deepest.get(old_node.part_number)
        fields = copied_child_fields(
            old_node=old_node,
            file_row=file_row,
            has_add_part=has_add_part,
            number_map=number_map,
        )
        if fields is None:
            not_install_count += 1
            continue
        parent_new_id = id_remap.get(old_node.parent_id) if old_node.parent_id else new_l0_id
        if parent_new_id is None:
            continue
        new_id = _insert_node(
            session,
            parent_id=parent_new_id,
            level=int(old_node.level),
            part_number=new_number,
            part_name=fields.part_name,
            qty=fields.qty,
            qty_unit=old_node.qty_unit,
            qty_text=fields.qty_text,
            node_role=old_node.node_role,
            is_supply_unit=old_node.is_supply_unit,
            material=fields.material,
            thickness_mm=fields.thickness_mm,
            thickness_text=fields.thickness_text,
            material_mill=fields.material_mill,
            part_weight=fields.part_weight,
            gauge_developed=fields.gauge_developed,
            weld_info=fields.weld_info,
            remark=fields.remark,
            internal_number=internal_from_file(file_row, old_node.internal_number),
            sort_no=old_node.sort_no or 0,
            seq_no=None,
            excel_row=old_node.excel_row,
            sketch_url=copied_sketch_url(
                location=session.location,
                vehicle_model=session.vehicle_model,
                bom_version=session.bom_version,
                part_number=new_number,
                file_row=file_row,
                old_sketch_url=old_node.sketch_url,
                copy_old_sketch=new_number == (old_node.part_number or "").strip(),
            ),
            excel_filename=old_node.excel_filename,
            excel_sheet_name=old_node.excel_sheet_name,
            excel_part_col=old_node.excel_part_col,
        )
        id_remap[old_node.id] = new_id
        stack.extend(old_children.get(old_node.id, []))
    return not_install_count


def _insert_added_parts(
    session: _PlantSession,
    *,
    all_specs: Sequence[BomChangePlantSpec],
    parsed_nodes: list[BomParsedNode],
    file_by_deepest: dict[str, BomParsedNode],
    number_map: dict[str, str | None],
    new_l0_id: int,
    id_remap: dict[int, int],
) -> None:
    planted = session.bom_service.list_subtree_nodes(session.db, root_id=new_l0_id)
    new_tree_numbers = {node.part_number for node in planted}
    excel_row_by_part = {node.part_number: node.excel_row for node in planted}
    pending_adds: list[tuple[int, BomChangePlantSpec, BomParsedNode, str]] = []
    for item in all_specs:
        after_part_number = item.after_part_number
        if (
            item.change_type != CHANGE_TYPE_ADD_PART
            or not after_part_number
            or after_part_number in new_tree_numbers
        ):
            continue
        add_row = file_by_deepest.get(after_part_number)
        if add_row is None:
            raise BusinessException(EC_BOM_NEW_ROOT)
        pending_adds.append((add_row.source_row or 0, item, add_row, after_part_number))
    pending_adds.sort(key=lambda row: row[0])
    for _, item, add_row, after_part_number in pending_adds:
        if add_row.qty is None or Decimal(str(add_row.qty)) <= 0:
            raise BusinessException(EC_QTY_CHANGED)
        if NOT_INSTALL_REMARK in (add_row.remark or ""):
            raise BusinessException(EC_NOT_INSTALL_SIGNAL)
        parent_id = new_l0_id
        if add_row.level == 2 and add_row.parent_index is not None:
            parent_parsed = parsed_nodes[add_row.parent_index]
            mapped_parent = number_map.get(parent_parsed.part_number, parent_parsed.part_number)
            for node_id in id_remap.values():
                parent_node = session.bom_service.get_node_row(session.db, node_id)
                if parent_node is not None and parent_node.part_number == mapped_parent:
                    parent_id = node_id
                    break
        add_excel_row = excel_row_for_added_part(
            add_row=add_row,
            parsed_nodes=parsed_nodes,
            excel_row_by_part=excel_row_by_part,
        )
        _insert_node(
            session,
            parent_id=parent_id,
            level=int(add_row.level),
            part_number=after_part_number,
            part_name=item.part_name or add_row.part_name,
            qty=add_row.qty,
            qty_unit=add_row.qty_unit,
            qty_text=add_row.qty_text,
            node_role=add_row.node_role,
            is_supply_unit=add_row.is_supply_unit,
            material=add_row.material,
            thickness_mm=add_row.thickness_mm,
            thickness_text=add_row.thickness_text,
            material_mill=add_row.material_mill,
            part_weight=add_row.part_weight,
            gauge_developed=add_row.gauge_developed,
            weld_info=add_row.weld_info,
            remark=add_row.remark,
            internal_number=add_row.internal_number,
            sort_no=add_row.sort_no or 0,
            seq_no=None,
            excel_row=add_excel_row,
            sketch_url=copied_sketch_url(
                location=session.location,
                vehicle_model=session.vehicle_model,
                bom_version=session.bom_version,
                part_number=after_part_number,
                file_row=add_row,
                old_sketch_url=None,
            ),
        )
        new_tree_numbers.add(after_part_number)
        excel_row_by_part[after_part_number] = add_excel_row


def _insert_node(
    session: _PlantSession,
    *,
    parent_id: int | None,
    level: int,
    part_number: str,
    part_name: str | None,
    qty: Decimal | None,
    qty_unit: str | None,
    qty_text: str | None,
    node_role: str,
    is_supply_unit: bool,
    material: str | None,
    thickness_mm: Decimal | None,
    thickness_text: str | None,
    material_mill: str | None,
    part_weight: Decimal | None,
    gauge_developed: str | None,
    weld_info: str | None,
    remark: str | None,
    internal_number: str | None,
    sort_no: int,
    seq_no: int | None,
    excel_row: int | None,
    sketch_url: str | None = None,
    excel_filename: str | None = None,
    excel_sheet_name: str | None = None,
    excel_part_col: int | None = None,
) -> int:
    row = session.bom_service.create_engineering_change_node(
        session.db,
        BomNodeWrite(
            snapshot_id=session.snapshot_id,
            parent_id=parent_id,
            level=level,
            sort_no=sort_no,
            seq_no=seq_no,
            internal_number=internal_number,
            part_number=part_number,
            part_name=part_name,
            qty=qty,
            qty_unit=qty_unit or "pcs",
            qty_text=qty_text,
            node_role=node_role,
            is_supply_unit=bool(is_supply_unit),
            material=material,
            thickness_mm=thickness_mm,
            thickness_text=thickness_text,
            material_mill=material_mill,
            part_weight=part_weight,
            gauge_developed=gauge_developed,
            weld_info=weld_info,
            remark=remark,
            sketch_url=sketch_url,
            excel_filename=excel_filename,
            excel_sheet_name=excel_sheet_name,
            excel_row=excel_row,
            excel_part_col=(
                excel_part_col
                if excel_part_col is not None
                else _EXCEL_PART_COL_BY_LEVEL.get(level)
            ),
            location=session.location,
            vehicle_model=session.vehicle_model,
            bom_version=session.bom_version,
            effective_year=session.effective_year,
            effective_month=session.effective_month,
            expiry_year=session.expiry_year,
            expiry_month=session.expiry_month,
            created_by=session.created_by,
            updated_by=session.updated_by,
        ),
    )
    return row.id
