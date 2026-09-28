"""采购对象列表 — 工程变更种树后按新树插行（不走整包 generate）。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.engineering_change_gates import (
    EC_AFTER_ROOT_MISSING,
    EC_PROCUREMENT_LIST_REQUIRED_DETAIL,
)
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom.node import BomNode, BomSnapshot
from app.models.bom.procurement_object import BomProcurementObject, BomProcurementObjectList
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.trees import collect_subtree
from app.services.bom.procurement_object.classify import (
    SECTION_OBJECT,
    ClassifiedRow,
    classify_nodes,
)
from app.services.bom.procurement_object.row_write import (
    ConfirmByNode,
    ConfirmTuple,
    build_object_row_write,
)

logger = logging.getLogger("service.bom.procurement_object.insert")


class BomProcurementObjectInsertService:
    """工程变更插行门面：无清单头拒收；同号或树上同一位置抄确认；不删旧行。"""

    def __init__(self) -> None:
        self.snapshot_repo = BomSnapshotRepository()
        self.node_repo = BomNodeRepository()
        self.repository = BomProcurementObjectRepository()

    def insert_for_new_tree(
        self,
        db: Session,
        *,
        snapshot_id: int,
        new_l0_id: int,
        old_l0_id: int | None,
        current_user: UserVO,
    ) -> list[int]:
        """
        只扫新树节点分类后插行。返回新插入对象行 id。
        调用方负责外层事务；本方法不 commit。
        """
        snapshot = self.snapshot_repo.get_by_id(db, snapshot_id)
        if snapshot is None:
            raise NotFoundException("未找到对应材料清单")
        all_nodes = self.node_repo.list_by_snapshot(db, snapshot_id)
        new_tree = collect_subtree(all_nodes, new_l0_id)
        if not new_tree:
            raise BusinessException(
                f"{EC_AFTER_ROOT_MISSING}。设变后的总成在系统里没有零件，不能插采购对象。"
            )
        old_tree = collect_subtree(all_nodes, old_l0_id) if old_l0_id else []
        old_by_number = self._index_old_object_rows(db, snapshot_id, old_tree)
        new_to_old = _new_to_old_part_numbers(old_tree, new_tree)

        classified = classify_nodes(new_tree)
        audit = audit_create(current_user)
        header = self._require_header(db, snapshot=snapshot)

        confirm_by_node: ConfirmByNode = {}
        for row in classified.rows:
            confirm = self._resolve_confirm(row, old_by_number, new_to_old)
            if confirm is not None:
                confirm_by_node[row.source_node_id] = confirm
        payloads = [
            build_object_row_write(
                db,
                row,
                list_id=header.id,
                confirm_by_node=confirm_by_node,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
            for row in classified.rows
        ]
        inserted_ids = self.repository.bulk_create_objects(db, payloads)
        logger.info(
            "工程变更插采购对象 snapshot=%s l0=%s count=%s",
            snapshot_id,
            new_l0_id,
            len(inserted_ids),
        )
        return inserted_ids

    def _require_header(
        self,
        db: Session,
        *,
        snapshot: BomSnapshot,
    ) -> BomProcurementObjectList:
        existing = self.repository.get_list_by_snapshot_id(db, snapshot.id)
        if existing is None:
            raise BusinessException(EC_PROCUREMENT_LIST_REQUIRED_DETAIL)
        return existing

    def _index_old_object_rows(
        self,
        db: Session,
        snapshot_id: int,
        old_tree: list[BomNode],
    ) -> dict[tuple[str, str, str | None], BomProcurementObject]:
        """(part_number, section, object_kind) → 旧树对象行。"""
        header = self.repository.get_list_by_snapshot_id(db, snapshot_id)
        if header is None or not old_tree:
            return {}
        old_node_ids = {node.id for node in old_tree}
        indexed: dict[tuple[str, str, str | None], BomProcurementObject] = {}
        for row in self.repository.list_objects_by_list_id(db, header.id):
            if row.source_node_id not in old_node_ids:
                continue
            indexed[(row.part_number, row.section, row.object_kind)] = row
        return indexed

    def _resolve_confirm(
        self,
        row: ClassifiedRow,
        old_by_number: dict[tuple[str, str, str | None], BomProcurementObject],
        new_to_old: dict[str, str],
    ) -> ConfirmTuple | None:
        if row.section != SECTION_OBJECT:
            return None
        key = (row.part_number, row.section, row.object_kind)
        old = old_by_number.get(key)
        if old is None:
            old_number = new_to_old.get(row.part_number)
            if old_number:
                old = old_by_number.get((old_number, row.section, row.object_kind))
        if old is None:
            return ("pending", None, None, None, None)
        return (
            old.confirm_status or "pending",
            old.confirmed_by,
            old.confirmed_at,
            old.confirm_remark,
            old.supplier_name,
        )


def _new_to_old_part_numbers(old_tree: list[BomNode], new_tree: list[BomNode]) -> dict[str, str]:
    """新树零件号 → 旧树同一位置（sort_no）零件号。不按字母版本配对。"""
    if not old_tree or not new_tree:
        return {}
    old_root = next((node for node in old_tree if int(node.level) == 0), None)
    new_root = next((node for node in new_tree if int(node.level) == 0), None)
    if old_root is None or new_root is None:
        return {}
    old_children: dict[int | None, list[BomNode]] = {}
    new_children: dict[int | None, list[BomNode]] = {}
    for node in old_tree:
        old_children.setdefault(node.parent_id, []).append(node)
    for node in new_tree:
        new_children.setdefault(node.parent_id, []).append(node)
    mapping: dict[str, str] = {}
    stack = [(old_root, new_root)]
    while stack:
        old_node, new_node = stack.pop()
        old_number = (old_node.part_number or "").strip()
        new_number = (new_node.part_number or "").strip()
        if old_number and new_number:
            mapping[new_number] = old_number
        old_kids = sorted(
            old_children.get(old_node.id, []),
            key=lambda node: (node.sort_no or 0, node.id or 0),
        )
        new_kids = sorted(
            new_children.get(new_node.id, []),
            key=lambda node: (node.sort_no or 0, node.id or 0),
        )
        old_by_sort = {kid.sort_no: kid for kid in old_kids}
        for new_kid in new_kids:
            old_kid = old_by_sort.get(new_kid.sort_no)
            if old_kid is not None:
                stack.append((old_kid, new_kid))
    return mapping
