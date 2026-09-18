"""采购对象清单 — 合册种树后按新树插行（不走整包 generate）。"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.engineering_change_gates import (
    is_letter_version_bump,
    letter_version_base,
)
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom.node import BomNode, BomSnapshot
from app.models.bom.procurement_object import BomProcurementObject
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectListWrite,
    BomProcurementObjectWrite,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom_service import _collect_subtree
from app.services.bom.procurement_object.classify import (
    SECTION_OBJECT,
    ClassifiedRow,
    classify_nodes,
)
from app.services.bom.procurement_object.generate_service import (
    BomProcurementObjectGenerateService,
)

logger = logging.getLogger("service.bom.procurement_object.insert")


class BomProcurementObjectInsertService:
    """合册插行门面：无头建空头；同号/字母版本抄确认；不删旧行。"""

    def __init__(self) -> None:
        self.snapshot_repo = BomSnapshotRepository()
        self.node_repo = BomNodeRepository()
        self.repository = BomProcurementObjectRepository()
        self._generate = BomProcurementObjectGenerateService()

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
        new_tree = _collect_subtree(all_nodes, new_l0_id)
        if not new_tree:
            raise BusinessException("新交货总成树为空，无法插采购对象")
        old_tree = _collect_subtree(all_nodes, old_l0_id) if old_l0_id else []
        old_by_number = self._index_old_object_rows(db, snapshot_id, old_tree)

        classified = classify_nodes(new_tree)
        audit = audit_create(current_user)
        header = self.repository.get_list_by_snapshot_id(db, snapshot_id)
        if header is None:
            header = self.repository.create_list(
                db,
                BomProcurementObjectListWrite(
                    snapshot_id=snapshot.id,
                    location=snapshot.location,
                    vehicle_model=snapshot.vehicle_model,
                    bom_version=snapshot.bom_version,
                    source_filename=snapshot.source_filename or "",
                    qa_passed=True,
                    qa_error_text=None,
                    l0_count=0,
                    l0_with_children_count=0,
                    l2_count=0,
                    subassembly_child_sum=0,
                    object_l0_degenerate_count=0,
                    object_l1_subassembly_count=0,
                    object_l1_stamping_count=0,
                    other_leaf_count=0,
                    anomaly_count=0,
                    generated_at=now(),
                    generated_by=display_name(current_user),
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )

        payloads: list[BomProcurementObjectWrite] = []
        for row in classified.rows:
            confirm = self._resolve_confirm(row, old_by_number)
            confirm_map: dict[
                int, tuple[str, str | None, datetime | None, str | None, str | None]
            ] = {}
            if confirm is not None:
                confirm_map[row.source_node_id] = confirm
            payloads.append(
                self._generate._row_write(
                    db,
                    row,
                    list_id=header.id,
                    confirm_by_node=confirm_map,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                )
            )
        inserted_ids: list[int] = []
        for payload in payloads:
            from app.repositories.persist import model_from_payload

            obj = model_from_payload(BomProcurementObject, payload)
            db.add(obj)
            db.flush()
            inserted_ids.append(obj.id)
        logger.info(
            "合册插采购对象 snapshot=%s l0=%s count=%s",
            snapshot_id,
            new_l0_id,
            len(inserted_ids),
        )
        return inserted_ids

    def ensure_empty_list_id(
        self,
        db: Session,
        *,
        snapshot: BomSnapshot,
        current_user: UserVO,
    ) -> tuple[int, bool]:
        """返回 (list_id, newly_created)。"""
        existing = self.repository.get_list_by_snapshot_id(db, snapshot.id)
        if existing is not None:
            return existing.id, False
        audit = audit_create(current_user)
        header = self.repository.create_list(
            db,
            BomProcurementObjectListWrite(
                snapshot_id=snapshot.id,
                location=snapshot.location,
                vehicle_model=snapshot.vehicle_model,
                bom_version=snapshot.bom_version,
                source_filename=snapshot.source_filename or "",
                qa_passed=True,
                qa_error_text=None,
                l0_count=0,
                l0_with_children_count=0,
                l2_count=0,
                subassembly_child_sum=0,
                object_l0_degenerate_count=0,
                object_l1_subassembly_count=0,
                object_l1_stamping_count=0,
                other_leaf_count=0,
                anomaly_count=0,
                generated_at=now(),
                generated_by=display_name(current_user),
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        return header.id, True

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
    ) -> tuple[str, str | None, datetime | None, str | None, str | None] | None:
        if row.section != SECTION_OBJECT:
            return None
        key = (row.part_number, row.section, row.object_kind)
        old = old_by_number.get(key)
        if old is None:
            base = letter_version_base(row.part_number)
            if base is not None:
                for (part_number, section, kind), candidate in old_by_number.items():
                    if section != row.section or kind != row.object_kind:
                        continue
                    if letter_version_base(part_number) != base:
                        continue
                    if is_letter_version_bump(part_number, row.part_number):
                        old = candidate
                        break
        if old is None:
            return ("pending", None, None, None, None)
        return (
            old.confirm_status or "pending",
            old.confirmed_by,
            old.confirmed_at,
            old.confirm_remark,
            old.supplier_name,
        )
