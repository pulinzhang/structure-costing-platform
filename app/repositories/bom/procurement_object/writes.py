"""采购对象列表写入：建清单、批量建对象、审核/反审、删待审。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom.procurement_object import (
    BomProcurementObject,
    BomProcurementObjectList,
)
from app.models.bom.procurement_object_generate_log import BomProcurementObjectGenerateLog
from app.repositories.bom.procurement_object.queries import BomProcurementObjectQueries
from app.repositories.bom.procurement_object.types import SECTION_OBJECT
from app.repositories.persist import model_from_payload, query_update
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectGenerateLogWrite,
    BomProcurementObjectListWrite,
    BomProcurementObjectWrite,
)


class BomProcurementObjectWrites:
    def __init__(self, queries: BomProcurementObjectQueries | None = None) -> None:
        self._queries = queries or BomProcurementObjectQueries()

    def create_list(
        self, db: Session, payload: BomProcurementObjectListWrite
    ) -> BomProcurementObjectList:
        row = model_from_payload(BomProcurementObjectList, payload)
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def bulk_create_objects(
        self, db: Session, payloads: list[BomProcurementObjectWrite]
    ) -> list[int]:
        rows: list[BomProcurementObject] = []
        for payload in payloads:
            row = model_from_payload(BomProcurementObject, payload)
            db.add(row)
            rows.append(row)
        if rows:
            db.flush()
        return [row.id for row in rows]

    def delete_list(self, db: Session, header: BomProcurementObjectList) -> None:
        db.delete(header)
        db.flush()

    def approve_objects_by_list_id(
        self,
        db: Session,
        *,
        list_id: int,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str,
        updated_by: str,
    ) -> int:
        count = query_update(
            db.query(BomProcurementObject).filter(
                BomProcurementObject.list_id == list_id,
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_PENDING,
            ),
            {
                "audit_status": AUDIT_APPROVED,
                "audited_by": audited_by,
                "audited_at": audited_at,
                "audit_remark": audit_remark,
                "updated_by": updated_by,
            },
        )
        db.flush()
        return count

    def approve_objects_by_ids(
        self,
        db: Session,
        *,
        object_ids: list[int],
        audited_by: str,
        audited_at: datetime,
        audit_remark: str,
        updated_by: str,
    ) -> int:
        if not object_ids:
            return 0
        count = query_update(
            db.query(BomProcurementObject).filter(
                BomProcurementObject.id.in_(object_ids),
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_PENDING,
            ),
            {
                "audit_status": AUDIT_APPROVED,
                "audited_by": audited_by,
                "audited_at": audited_at,
                "audit_remark": audit_remark,
                "updated_by": updated_by,
            },
        )
        db.flush()
        return count

    def reverse_objects_by_list_id(
        self,
        db: Session,
        *,
        list_id: int,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str,
    ) -> int:
        count = query_update(
            db.query(BomProcurementObject).filter(
                BomProcurementObject.list_id == list_id,
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_APPROVED,
            ),
            {
                "audit_status": AUDIT_PENDING,
                "reverse_audited_by": reverse_audited_by,
                "reverse_audited_at": reverse_audited_at,
                "reverse_audit_remark": reverse_audit_remark,
                "updated_by": updated_by,
            },
        )
        db.flush()
        return count

    def reverse_objects_by_ids(
        self,
        db: Session,
        *,
        object_ids: list[int],
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str,
    ) -> int:
        if not object_ids:
            return 0
        count = query_update(
            db.query(BomProcurementObject).filter(
                BomProcurementObject.id.in_(object_ids),
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_APPROVED,
            ),
            {
                "audit_status": AUDIT_PENDING,
                "reverse_audited_by": reverse_audited_by,
                "reverse_audited_at": reverse_audited_at,
                "reverse_audit_remark": reverse_audit_remark,
                "updated_by": updated_by,
            },
        )
        db.flush()
        return count

    def delete_pending_objects_by_list_id(self, db: Session, list_id: int) -> int:
        count = (
            db.query(BomProcurementObject)
            .filter(
                BomProcurementObject.list_id == list_id,
                BomProcurementObject.audit_status == AUDIT_PENDING,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(count)

    def delete_objects_by_source_node_ids(
        self,
        db: Session,
        *,
        list_id: int,
        source_node_ids: list[int],
    ) -> int:
        if not source_node_ids:
            return 0
        count = (
            db.query(BomProcurementObject)
            .filter(
                BomProcurementObject.list_id == list_id,
                BomProcurementObject.source_node_id.in_(source_node_ids),
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(count)

    def delete_pending_objects_by_ids(self, db: Session, object_ids: list[int]) -> int:
        if not object_ids:
            return 0
        count = (
            db.query(BomProcurementObject)
            .filter(
                BomProcurementObject.id.in_(object_ids),
                BomProcurementObject.audit_status == AUDIT_PENDING,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(count)

    def delete_object(self, db: Session, row: BomProcurementObject) -> None:
        """删单条采购对象行。只 flush。"""
        db.delete(row)
        db.flush()

    def recount_header_from_rows(self, db: Session, header: BomProcurementObjectList) -> None:
        """有已审时批量删除 pending 后重算计数，并标记检测未通过。工程变更回滚禁止调用。"""
        rows = self._queries.list_objects_by_list_id(db, header.id)
        header.object_l0_degenerate_count = sum(
            1 for row in rows if row.object_kind == "l0_degenerate"
        )
        header.object_l1_subassembly_count = sum(
            1 for row in rows if row.object_kind == "l1_subassembly"
        )
        header.object_l1_stamping_count = sum(1 for row in rows if row.object_kind == "l1_stamping")
        header.other_leaf_count = sum(1 for row in rows if row.section == "other_leaf")
        header.anomaly_count = sum(1 for row in rows if row.section == "anomaly")
        header.qa_passed = False
        header.qa_error_text = "清单已被部分删除，须重新生成后才能审核"
        db.flush()

    def create_generate_log(
        self, db: Session, data: BomProcurementObjectGenerateLogWrite
    ) -> BomProcurementObjectGenerateLog:
        record = model_from_payload(BomProcurementObjectGenerateLog, data)
        db.add(record)
        db.flush()
        return record
