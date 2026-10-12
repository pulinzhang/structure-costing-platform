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
    CHANGE_TYPE_ADD_SUBASSEMBLY,
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
    has_add_part = any(
        item.change_type in {CHANGE_TYPE_ADD_PART, CHANGE_TYPE_ADD_SUBASSEMBLY}
        for item in all_specs
    )
    has_not_install = any(item.change_type == CHANGE_TYPE_NOT_INSTALL for item in all_specs)
    number_map = build_number_map(spec, old_nodes, parsed_nodes, extra_specs)
    file_by_deepest = {node.part_number: node for node in parsed_nodes if node.level != 0}
    subassembly_children = _subassembly_child_rows(all_specs, parsed_nodes)
    placed_under_new = {(node.part_number or "").strip() for node in subassembly_children}
    _assert_add_and_not_install(all_specs, old_nodes, parsed_nodes)

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
        placed_under_new=placed_under_new,
    )
    _insert_added_parts(
        session,
        all_specs=all_specs,
        parsed_nodes=parsed_nodes,
        file_by_deepest=file_by_deepest,
        number_map=number_map,
        new_l0_id=new_l0_id,
        id_remap=id_remap,
        old_by_id=old_by_id,
        subassembly_children=subassembly_children,
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
    parsed_nodes: list[BomParsedNode],
) -> None:
    old_numbers = {(node.part_number or "").strip() for node in old_nodes}
    for item in all_specs:
        if (
            item.change_type in {CHANGE_TYPE_ADD_PART, CHANGE_TYPE_ADD_SUBASSEMBLY}
            and item.after_part_number
            and item.after_part_number.strip() in old_numbers
        ):
            raise BusinessException(EC_ADD_ALREADY_ON_TREE)
        if item.change_type == CHANGE_TYPE_NOT_INSTALL and item.before_part_number:
            before_number = item.before_part_number.strip()
            if not _has_not_install_mark(parsed_nodes, before_number):
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
    placed_under_new: set[str],
) -> int:
    not_install_count = 0
    stack = list(old_children.get(old_l0.id, []))
    while stack:
        old_node = stack.pop(0)
        part_number = (old_node.part_number or "").strip()
        new_number = number_map.get(old_node.part_number, old_node.part_number)
        if new_number is None:
            not_install_count += 1
            continue
        # 清单把这个号写在新分总成下面时，旧位置不另抄一份。
        if part_number in placed_under_new and new_number == part_number:
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
    old_by_id: dict[int, BomNode],
    subassembly_children: list[BomParsedNode],
) -> None:
    planted = session.bom_service.list_subtree_nodes(session.db, root_id=new_l0_id)
    new_tree_numbers = {node.part_number for node in planted}
    excel_row_by_part = {node.part_number: node.excel_row for node in planted}
    inserted_ids: dict[str, int] = {}
    pending_adds: list[tuple[int, BomChangePlantSpec, BomParsedNode, str]] = []
    for item in all_specs:
        after_part_number = item.after_part_number
        if (
            item.change_type not in {CHANGE_TYPE_ADD_PART, CHANGE_TYPE_ADD_SUBASSEMBLY}
            or not after_part_number
            or after_part_number in new_tree_numbers
        ):
            continue
        add_row = file_by_deepest.get(after_part_number)
        if add_row is None:
            raise BusinessException(EC_BOM_NEW_ROOT)
        pending_adds.append((add_row.source_row or 0, item, add_row, after_part_number))
    pending_adds.sort(key=lambda row: (int(row[2].level), row[0]))
    for _, item, add_row, after_part_number in pending_adds:
        if add_row.qty is None or Decimal(str(add_row.qty)) <= 0:
            raise BusinessException(EC_QTY_CHANGED)
        if NOT_INSTALL_REMARK in (add_row.remark or ""):
            raise BusinessException(EC_NOT_INSTALL_SIGNAL)
        parent_id = _added_parent_id(
            session,
            add_row=add_row,
            parsed_nodes=parsed_nodes,
            number_map=number_map,
            new_l0_id=new_l0_id,
            id_remap=id_remap,
            inserted_ids=inserted_ids,
        )
        add_excel_row = excel_row_for_added_part(
            add_row=add_row,
            parsed_nodes=parsed_nodes,
            excel_row_by_part=excel_row_by_part,
        )
        sort_no = add_row.sort_no or 0
        new_id = _insert_node(
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
            sort_no=sort_no,
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
        inserted_ids[after_part_number] = new_id
        new_tree_numbers.add(after_part_number)
        excel_row_by_part[after_part_number] = add_excel_row
    _insert_subassembly_children(
        session,
        parsed_nodes=parsed_nodes,
        old_by_id=old_by_id,
        inserted_ids=inserted_ids,
        id_remap=id_remap,
        new_tree_numbers=new_tree_numbers,
        subassembly_children=subassembly_children,
    )


def _insert_subassembly_children(
    session: _PlantSession,
    *,
    parsed_nodes: list[BomParsedNode],
    old_by_id: dict[int, BomNode],
    inserted_ids: dict[str, int],
    id_remap: dict[int, int],
    new_tree_numbers: set[str],
    subassembly_children: list[BomParsedNode],
) -> None:
    """新分总成下面，材料清单写了几颗就插几颗。"""
    for file_row in subassembly_children:
        number = (file_row.part_number or "").strip()
        if number in new_tree_numbers:
            continue
        parent_index = file_row.parent_index
        if parent_index is None:
            continue
        parent = parsed_nodes[parent_index]
        parent_id = inserted_ids.get((parent.part_number or "").strip())
        if parent_id is None:
            raise BusinessException(EC_BOM_NEW_ROOT)
        old_node = _old_node_by_number(old_by_id, number)
        new_id = _insert_node(
            session,
            parent_id=parent_id,
            level=int(file_row.level),
            part_number=number,
            part_name=file_row.part_name or (old_node.part_name if old_node else None),
            qty=file_row.qty,
            qty_unit=file_row.qty_unit or (old_node.qty_unit if old_node else "pcs"),
            qty_text=file_row.qty_text or (old_node.qty_text if old_node else None),
            node_role=file_row.node_role or (old_node.node_role if old_node else "make"),
            is_supply_unit=old_node.is_supply_unit if old_node else False,
            material=file_row.material or (old_node.material if old_node else None),
            thickness_mm=file_row.thickness_mm
            if file_row.thickness_mm is not None
            else (old_node.thickness_mm if old_node else None),
            thickness_text=file_row.thickness_text
            or (old_node.thickness_text if old_node else None),
            material_mill=file_row.material_mill or (old_node.material_mill if old_node else None),
            part_weight=file_row.part_weight
            if file_row.part_weight is not None
            else (old_node.part_weight if old_node else None),
            gauge_developed=file_row.gauge_developed
            or (old_node.gauge_developed if old_node else None),
            weld_info=file_row.weld_info or (old_node.weld_info if old_node else None),
            remark=file_row.remark,
            internal_number=internal_from_file(
                file_row, old_node.internal_number if old_node else None
            ),
            sort_no=file_row.sort_no or 0,
            seq_no=None,
            excel_row=file_row.source_row,
            sketch_url=copied_sketch_url(
                location=session.location,
                vehicle_model=session.vehicle_model,
                bom_version=session.bom_version,
                part_number=number,
                file_row=file_row,
                old_sketch_url=old_node.sketch_url if old_node else None,
                copy_old_sketch=old_node is not None,
            ),
        )
        if old_node is not None and int(old_node.level) == 1:
            id_remap[old_node.id] = new_id
        inserted_ids[number] = new_id
        new_tree_numbers.add(number)


def _subassembly_child_rows(
    specs: Sequence[BomChangePlantSpec],
    parsed_nodes: list[BomParsedNode],
) -> list[BomParsedNode]:
    """新分总成下面用量大于 0 的零件行。"""
    subassembly_numbers = _subassembly_numbers(specs)
    rows = [
        node
        for node in parsed_nodes
        if int(node.level) >= 2
        and (node.part_number or "").strip()
        and _hangs_under_subassembly(parsed_nodes, node, subassembly_numbers)
        and node.qty is not None
        and Decimal(str(node.qty)) > 0
        and NOT_INSTALL_REMARK not in (node.remark or "")
        and node.parent_index is not None
    ]
    rows.sort(key=lambda node: (int(node.level), node.source_row or 0))
    return rows


def _subassembly_numbers(specs: Sequence[BomChangePlantSpec]) -> set[str]:
    return {
        (item.after_part_number or "").strip()
        for item in specs
        if item.change_type == CHANGE_TYPE_ADD_SUBASSEMBLY
        and (item.after_part_number or "").strip()
    }


def _hangs_under_subassembly(
    parsed_nodes: list[BomParsedNode],
    node: BomParsedNode,
    subassembly_numbers: set[str],
) -> bool:
    current = node
    while current.parent_index is not None:
        parent = parsed_nodes[current.parent_index]
        if int(parent.level) == 1 and (parent.part_number or "").strip() in subassembly_numbers:
            return True
        current = parent
    return False


def _has_not_install_mark(parsed_nodes: list[BomParsedNode], part_number: str) -> bool:
    for node in parsed_nodes:
        if int(node.level) == 0 or (node.part_number or "").strip() != part_number:
            continue
        if is_not_install_row(node.qty, node.remark, part_number=part_number):
            return True
    return False


def _old_node_by_number(old_by_id: dict[int, BomNode], part_number: str) -> BomNode | None:
    found: BomNode | None = None
    for node in old_by_id.values():
        if (node.part_number or "").strip() != part_number:
            continue
        if int(node.level) == 1:
            return node
        found = node
    return found


def _added_parent_id(
    session: _PlantSession,
    *,
    add_row: BomParsedNode,
    parsed_nodes: list[BomParsedNode],
    number_map: dict[str, str | None],
    new_l0_id: int,
    id_remap: dict[int, int],
    inserted_ids: dict[str, int],
) -> int:
    if add_row.level != 2 or add_row.parent_index is None:
        return new_l0_id
    parent_parsed = parsed_nodes[add_row.parent_index]
    parent_number = (parent_parsed.part_number or "").strip()
    mapped_parent = number_map.get(parent_number, parent_number)
    if mapped_parent and mapped_parent in inserted_ids:
        return inserted_ids[mapped_parent]
    if not mapped_parent:
        return new_l0_id
    for node_id in id_remap.values():
        parent_node = session.bom_service.get_node_row(session.db, node_id)
        if parent_node is not None and parent_node.part_number == mapped_parent:
            return node_id
    return new_l0_id


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
