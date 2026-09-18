"""工程变更合册种树：BOM 领域算法（只 flush，由调用方 commit）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    EC_ADD_ALREADY_ON_TREE,
    EC_BOM_NEW_ROOT,
    EC_NOT_INSTALL_SIGNAL,
    EC_QTY_CHANGED,
    NOT_INSTALL_REMARK,
    PART_LEVEL_ASSEMBLY,
    bump_letter_version,
    is_letter_version_bump,
    is_not_install_row,
    letter_version_suffix,
)
from app.config import settings
from app.exceptions.base import BusinessException
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import BomParsedNode
from app.schemas.dto.bom_dto import BomNodeWrite
from app.schemas.vo.user_vo import UserVO

if TYPE_CHECKING:
    from app.services.bom.bom_service import BomService

_EXCEL_PART_COL_BY_LEVEL = {0: 3, 1: 9, 2: 14}


@dataclass(slots=True)
class BomChangePlantSpec:
    """种树所需工程变更单字段（与 EC ChangeOrderRowParsed 解耦，避免上游依赖 EC）。"""

    change_type: str
    before_assembly_part_number: str
    after_assembly_part_number: str | None
    assembly_name: str | None
    part_level: str
    before_part_number: str | None
    after_part_number: str | None
    part_name: str | None


@dataclass(slots=True)
class BomChangePlantResult:
    new_l0_id: int
    not_install_count: int = 0
    warnings: list[str] = field(default_factory=list)


def plant_change_tree(
    bom_service: BomService,
    db: Session,
    *,
    snapshot_id: int,
    location: str,
    vehicle_model: str,
    before_l0_id: int,
    seq_no: int | None,
    spec: BomChangePlantSpec,
    parsed_nodes: list[BomParsedNode],
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    current_user: UserVO,
    node_bom_version: str | None = None,
) -> BomChangePlantResult:
    """
    从旧树带走未改零件 + 合册变化行种新树。
    失效由调用方负责。只 flush。
    """
    snapshot_vo = bom_service.get_snapshot(db, snapshot_id)
    bom_version = (node_bom_version or "").strip() or snapshot_vo.bom_version
    audit = audit_create(current_user)

    old_nodes = bom_service.list_subtree_nodes(db, root_id=before_l0_id)
    old_by_id = {n.id: n for n in old_nodes}
    old_children: dict[int | None, list[BomNode]] = {}
    for node in old_nodes:
        old_children.setdefault(node.parent_id, []).append(node)

    file_l0 = [n for n in parsed_nodes if n.level == 0]
    if len(file_l0) != 1:
        raise BusinessException(EC_BOM_NEW_ROOT)
    if file_l0[0].part_number != spec.after_assembly_part_number:
        raise BusinessException(EC_BOM_NEW_ROOT)

    not_install_count = 0
    warnings: list[str] = []
    number_map = _build_number_map(spec, old_nodes, parsed_nodes)
    file_by_deepest = _index_file_change_rows(parsed_nodes)

    def map_number(old_number: str) -> str | None:
        if old_number in number_map and number_map[old_number] is None:
            return None
        return number_map.get(old_number, old_number)

    old_l0 = old_by_id[before_l0_id]
    if spec.change_type == CHANGE_TYPE_ADD_PART and spec.after_part_number:
        old_numbers = {(node.part_number or "").strip() for node in old_nodes}
        if spec.after_part_number.strip() in old_numbers:
            raise BusinessException(EC_ADD_ALREADY_ON_TREE)
    if spec.change_type == CHANGE_TYPE_NOT_INSTALL and spec.before_part_number:
        marked = file_by_deepest.get(spec.before_part_number.strip())
        if marked is None or not is_not_install_row(marked.qty, marked.remark):
            raise BusinessException(EC_NOT_INSTALL_SIGNAL)
    id_remap: dict[int, int] = {}

    def insert_node(
        *,
        parent_id: int | None,
        level: int,
        part_number: str,
        part_name: str | None,
        qty: Decimal | None,
        qty_unit: str,
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
        seq: int | None,
        excel_row: int | None,
        sketch_url: str | None = None,
    ) -> int:
        row = bom_service.create_engineering_change_node(
            db,
            BomNodeWrite(
                snapshot_id=snapshot_id,
                parent_id=parent_id,
                level=level,
                sort_no=sort_no,
                seq_no=seq,
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
                excel_filename=None,
                excel_sheet_name=None,
                excel_row=excel_row,
                excel_part_col=_EXCEL_PART_COL_BY_LEVEL.get(level),
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                effective_year=effective_year,
                effective_month=effective_month,
                expiry_year=expiry_year,
                expiry_month=expiry_month,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        return row.id

    new_l0_number = spec.after_assembly_part_number or bump_letter_version(
        spec.before_assembly_part_number
    )
    file_l0_sketch = next((node for node in file_l0 if node.sketch_bytes), file_l0[0])
    new_l0_id = insert_node(
        parent_id=None,
        level=0,
        part_number=new_l0_number,
        part_name=spec.assembly_name or old_l0.part_name,
        qty=old_l0.qty,
        qty_unit=old_l0.qty_unit or "pcs",
        qty_text=old_l0.qty_text,
        node_role=old_l0.node_role,
        is_supply_unit=bool(old_l0.is_supply_unit),
        material=old_l0.material,
        thickness_mm=old_l0.thickness_mm,
        thickness_text=old_l0.thickness_text,
        material_mill=old_l0.material_mill,
        part_weight=old_l0.part_weight,
        gauge_developed=old_l0.gauge_developed,
        weld_info=old_l0.weld_info,
        remark=old_l0.remark,
        internal_number=_internal_from_file(file_l0[0], old_l0.internal_number),
        sort_no=old_l0.sort_no or 0,
        seq=seq_no,
        excel_row=file_l0[0].source_row,
        sketch_url=_write_sketch_png(
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=new_l0_number,
            sort_no=file_l0[0].sort_no,
            png_bytes=file_l0_sketch.sketch_bytes,
        ),
    )
    id_remap[old_l0.id] = new_l0_id

    stack = list(old_children.get(old_l0.id, []))
    while stack:
        old_node = stack.pop(0)
        new_number = map_number(old_node.part_number)
        if new_number is None:
            not_install_count += 1
            continue
        file_row = file_by_deepest.get(new_number) or file_by_deepest.get(old_node.part_number)
        qty = old_node.qty
        if file_row is not None:
            if is_not_install_row(file_row.qty, file_row.remark):
                not_install_count += 1
                continue
            if (
                file_row.qty is not None
                and old_node.qty is not None
                and Decimal(str(file_row.qty)) != Decimal(str(old_node.qty))
                and spec.change_type != CHANGE_TYPE_ADD_PART
            ):
                raise BusinessException(EC_QTY_CHANGED)
            if spec.change_type == CHANGE_TYPE_ADD_PART and old_node.part_number not in number_map:
                qty = file_row.qty
            part_name = file_row.part_name or old_node.part_name
            material = file_row.material if file_row.material is not None else old_node.material
            weld_info = file_row.weld_info if file_row.weld_info is not None else old_node.weld_info
            remark = file_row.remark if file_row.remark is not None else old_node.remark
            thickness_mm = (
                file_row.thickness_mm
                if file_row.thickness_mm is not None
                else old_node.thickness_mm
            )
            excel_row = file_row.source_row
        else:
            part_name = old_node.part_name
            material = old_node.material
            weld_info = old_node.weld_info
            remark = old_node.remark
            thickness_mm = old_node.thickness_mm
            excel_row = old_node.excel_row

        parent_new_id = id_remap.get(old_node.parent_id) if old_node.parent_id else new_l0_id
        if parent_new_id is None:
            continue
        new_id = insert_node(
            parent_id=parent_new_id,
            level=int(old_node.level),
            part_number=new_number,
            part_name=part_name,
            qty=qty,
            qty_unit=old_node.qty_unit or "pcs",
            qty_text=old_node.qty_text,
            node_role=old_node.node_role,
            is_supply_unit=bool(old_node.is_supply_unit),
            material=material,
            thickness_mm=thickness_mm,
            thickness_text=old_node.thickness_text,
            material_mill=old_node.material_mill,
            part_weight=old_node.part_weight,
            gauge_developed=old_node.gauge_developed,
            weld_info=weld_info,
            remark=remark,
            internal_number=_internal_from_file(file_row, old_node.internal_number),
            sort_no=old_node.sort_no or 0,
            seq=None,
            excel_row=excel_row,
        )
        id_remap[old_node.id] = new_id
        stack.extend(old_children.get(old_node.id, []))

    new_tree_numbers = {
        n.part_number for n in bom_service.list_subtree_nodes(db, root_id=new_l0_id)
    }
    if (
        spec.change_type == CHANGE_TYPE_ADD_PART
        and spec.after_part_number
        and spec.after_part_number not in new_tree_numbers
    ):
        add_row = file_by_deepest.get(spec.after_part_number)
        if add_row is None:
            raise BusinessException(EC_BOM_NEW_ROOT)
        if add_row.qty is None or Decimal(str(add_row.qty)) <= 0:
            raise BusinessException(EC_QTY_CHANGED)
        if NOT_INSTALL_REMARK in (add_row.remark or ""):
            raise BusinessException(EC_NOT_INSTALL_SIGNAL)
        parent_id = new_l0_id
        if add_row.level == 2 and add_row.parent_index is not None:
            parent_parsed = parsed_nodes[add_row.parent_index]
            for nid in id_remap.values():
                parent_node = bom_service.get_node_row(db, nid)
                if parent_node is not None and parent_node.part_number == (
                    number_map.get(parent_parsed.part_number, parent_parsed.part_number)
                ):
                    parent_id = nid
                    break
        insert_node(
            parent_id=parent_id,
            level=int(add_row.level),
            part_number=spec.after_part_number,
            part_name=spec.part_name or add_row.part_name,
            qty=add_row.qty,
            qty_unit=add_row.qty_unit or "pcs",
            qty_text=add_row.qty_text,
            node_role=add_row.node_role,
            is_supply_unit=bool(add_row.is_supply_unit),
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
            seq=None,
            excel_row=add_row.source_row,
        )

    new_tree = bom_service.list_subtree_nodes(db, root_id=new_l0_id)
    if len(new_tree) <= 1 and spec.change_type != CHANGE_TYPE_ADD_PART:
        children = [n for n in new_tree if n.id != new_l0_id]
        if not children and spec.change_type == CHANGE_TYPE_NOT_INSTALL:
            raise BusinessException(EC_NOT_INSTALL_SIGNAL)

    return BomChangePlantResult(
        new_l0_id=new_l0_id,
        not_install_count=not_install_count,
        warnings=warnings,
    )


def _build_number_map(
    spec: BomChangePlantSpec,
    old_nodes: list[BomNode],
    parsed_nodes: list[BomParsedNode],
) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {
        spec.before_assembly_part_number: spec.after_assembly_part_number
    }
    if spec.change_type == CHANGE_TYPE_REVISE:
        if spec.part_level != PART_LEVEL_ASSEMBLY and spec.before_part_number:
            mapping[spec.before_part_number] = spec.after_part_number
            _map_revise_ancestor_chain(mapping, old_nodes, spec.before_part_number)
        _map_file_letter_bumps(mapping, old_nodes, parsed_nodes)
    elif spec.change_type == CHANGE_TYPE_NOT_INSTALL and spec.before_part_number:
        mapping[spec.before_part_number] = None
        if spec.after_assembly_part_number:
            mapping[spec.before_assembly_part_number] = spec.after_assembly_part_number
        _map_file_letter_bumps(mapping, old_nodes, parsed_nodes)
    elif spec.change_type == CHANGE_TYPE_ADD_PART:
        _map_file_letter_bumps(mapping, old_nodes, parsed_nodes)
    return mapping


def _map_revise_ancestor_chain(
    mapping: dict[str, str | None],
    old_nodes: list[BomNode],
    before_part_number: str,
) -> None:
    """改图那条链：从改图层走到交货总成，中间分总成整段换号。"""
    by_id = {node.id: node for node in old_nodes}
    current = next(
        (
            node
            for node in old_nodes
            if (node.part_number or "").strip() == before_part_number.strip()
        ),
        None,
    )
    if current is None:
        return
    parent_id = current.parent_id
    while parent_id:
        parent = by_id.get(parent_id)
        if parent is None or int(parent.level) == 0:
            break
        old_number = (parent.part_number or "").strip()
        parent_id = parent.parent_id
        if not old_number or old_number in mapping:
            continue
        if letter_version_suffix(old_number) is None:
            continue
        mapping[old_number] = bump_letter_version(old_number)


def _map_file_letter_bumps(
    mapping: dict[str, str | None],
    old_nodes: list[BomNode],
    parsed_nodes: list[BomParsedNode],
) -> None:
    """材料清单写出的上级新号盖到映射上（与工程变更单改图层一起构成整条链）。"""
    old_numbers = {
        (node.part_number or "").strip() for node in old_nodes if (node.part_number or "").strip()
    }
    mapped_news = {value for value in mapping.values() if value}
    for node in parsed_nodes:
        if int(node.level) == 0:
            continue
        file_number = (node.part_number or "").strip()
        if not file_number or file_number in old_numbers or file_number in mapped_news:
            continue
        candidates = [
            old_number
            for old_number in old_numbers
            if old_number not in mapping and is_letter_version_bump(old_number, file_number)
        ]
        if not candidates:
            continue
        candidates.sort(reverse=True)
        mapping[candidates[0]] = file_number
        mapped_news.add(file_number)


def _index_file_change_rows(parsed_nodes: list[BomParsedNode]) -> dict[str, BomParsedNode]:
    result: dict[str, BomParsedNode] = {}
    for node in parsed_nodes:
        if node.level == 0:
            continue
        result[node.part_number] = node
    return result


def _internal_from_file(file_row: BomParsedNode | None, old_value: str | None) -> str | None:
    if file_row is None:
        return old_value
    text = (file_row.internal_number or "").strip()
    if text:
        return text
    return old_value


def _write_sketch_png(
    *,
    location: str,
    vehicle_model: str,
    bom_version: str,
    part_number: str,
    sort_no: int,
    png_bytes: bytes | None,
) -> str | None:
    if not png_bytes:
        return None
    safe_location = _safe_segment(location)
    safe_vehicle = _safe_segment(vehicle_model)
    safe_version = _safe_segment(bom_version)
    relative_dir = Path("bom") / safe_location / safe_vehicle / safe_version / "sketches"
    target_dir = settings.UPLOAD_DIR / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_part = (
        "".join(
            ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in (part_number or "assembly")
        )
        or "assembly"
    )
    file_name = f"{sort_no}_{safe_part}.png"
    (target_dir / file_name).write_bytes(png_bytes)
    return str(relative_dir / file_name).replace("\\", "/")


def _safe_segment(value: str) -> str:
    text = (value or "").strip() or "unknown"
    for ch in ("/", "\\", ":", "*", "?", '"', "<", ">", "|", " "):
        text = text.replace(ch, "_")
    return text
