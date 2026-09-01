"""采购对象清单 Repository。"""

from datetime import datetime
from typing import TypedDict

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom.procurement_object import (
    BomProcurementObject,
    BomProcurementObjectList,
)
from app.models.bom.procurement_object_generate_log import BomProcurementObjectGenerateLog
from app.repositories.persist import model_from_payload, query_update
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectGenerateLogWrite,
    BomProcurementObjectListWrite,
    BomProcurementObjectWrite,
)
from app.services.bom.procurement_object.classify import SECTION_OBJECT


class ProcurementObjectAuditSummary(TypedDict):
    total_count: int
    pending_count: int
    approved_count: int
    object_count: int
    other_leaf_count: int
    anomaly_count: int


class ProcurementObjectListFilters(TypedDict):
    locations: list[str]
    vehicle_models: list[str]
    bom_versions: list[str]
    summary: ProcurementObjectAuditSummary


class BomProcurementObjectRepository:
    """采购对象清单数据访问。"""

    def get_list_by_id(self, db: Session, list_id: int) -> BomProcurementObjectList | None:
        return (
            db.query(BomProcurementObjectList)
            .filter(BomProcurementObjectList.id == list_id)
            .first()
        )

    def get_list_by_snapshot_id(
        self, db: Session, snapshot_id: int
    ) -> BomProcurementObjectList | None:
        return (
            db.query(BomProcurementObjectList)
            .filter(BomProcurementObjectList.snapshot_id == snapshot_id)
            .first()
        )

    def has_list_for_location(self, db: Session, location: str) -> bool:
        return (
            db.query(BomProcurementObjectList.id)
            .filter(BomProcurementObjectList.location == location)
            .first()
            is not None
        )

    def get_list_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomProcurementObjectList | None:
        return (
            db.query(BomProcurementObjectList)
            .filter(
                BomProcurementObjectList.location == location,
                BomProcurementObjectList.vehicle_model == vehicle_model,
                BomProcurementObjectList.bom_version == bom_version,
            )
            .first()
        )

    def get_object_by_id(self, db: Session, object_id: int) -> BomProcurementObject | None:
        return db.query(BomProcurementObject).filter(BomProcurementObject.id == object_id).first()

    def list_objects_by_list_id(self, db: Session, list_id: int) -> list[BomProcurementObject]:
        return (
            db.query(BomProcurementObject)
            .filter(BomProcurementObject.list_id == list_id)
            .order_by(BomProcurementObject.section, BomProcurementObject.id)
            .all()
        )

    def count_approved_objects(self, db: Session, list_id: int) -> int:
        return (
            db.query(BomProcurementObject)
            .filter(
                BomProcurementObject.list_id == list_id,
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_APPROVED,
            )
            .count()
        )

    def create_list(
        self, db: Session, payload: BomProcurementObjectListWrite
    ) -> BomProcurementObjectList:
        row = model_from_payload(BomProcurementObjectList, payload)
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def bulk_create_objects(self, db: Session, payloads: list[BomProcurementObjectWrite]) -> None:
        for payload in payloads:
            db.add(model_from_payload(BomProcurementObject, payload))
        db.flush()

    def delete_list(self, db: Session, header: BomProcurementObjectList) -> None:
        db.delete(header)
        db.flush()

    def paginate_objects(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        section: str | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
        audit_status: str | None = None,
        part_number: str | None = None,
        l0_part_number: str | None = None,
        excel_row: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomProcurementObject], int]:
        query = self._apply_object_filters(
            db.query(BomProcurementObject).join(BomProcurementObjectList),
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            section=section,
            object_kind=object_kind,
            confirm_status=confirm_status,
            audit_status=audit_status,
            part_number=part_number,
            l0_part_number=l0_part_number,
            excel_row=excel_row,
        )
        total = query.count()
        rows = self._apply_check_order(query).offset(skip).limit(limit).all()
        return rows, total

    def list_objects_for_export(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        section: str | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
        audit_status: str | None = None,
        part_number: str | None = None,
        l0_part_number: str | None = None,
        excel_row: int | None = None,
    ) -> list[BomProcurementObject]:
        query = self._apply_object_filters(
            db.query(BomProcurementObject).join(BomProcurementObjectList),
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            section=section,
            object_kind=object_kind,
            confirm_status=confirm_status,
            audit_status=audit_status,
            part_number=part_number,
            l0_part_number=l0_part_number,
            excel_row=excel_row,
        )
        return self._apply_check_order(query).all()

    def get_filter_options(self, db: Session) -> tuple[list[str], list[str], list[str]]:
        locations = [
            row[0]
            for row in db.query(BomProcurementObjectList.location)
            .distinct()
            .order_by(BomProcurementObjectList.location)
            .all()
            if row[0]
        ]
        models = [
            row[0]
            for row in db.query(BomProcurementObjectList.vehicle_model)
            .distinct()
            .order_by(BomProcurementObjectList.vehicle_model)
            .all()
            if row[0]
        ]
        versions = [
            row[0]
            for row in db.query(BomProcurementObjectList.bom_version)
            .distinct()
            .order_by(BomProcurementObjectList.bom_version)
            .all()
            if row[0]
        ]
        return locations, models, versions

    def summarize_objects(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        section: str | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
        audit_status: str | None = None,
        part_number: str | None = None,
        l0_part_number: str | None = None,
        excel_row: int | None = None,
    ) -> ProcurementObjectAuditSummary:
        base = self._apply_object_filters(
            db.query(BomProcurementObject).join(BomProcurementObjectList),
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            section=section,
            object_kind=object_kind,
            confirm_status=confirm_status,
            audit_status=audit_status,
            part_number=part_number,
            l0_part_number=l0_part_number,
            excel_row=excel_row,
        )
        total = base.count()
        pending = base.filter(
            BomProcurementObject.section == SECTION_OBJECT,
            BomProcurementObject.audit_status == AUDIT_PENDING,
        ).count()
        approved = base.filter(
            BomProcurementObject.section == SECTION_OBJECT,
            BomProcurementObject.audit_status == AUDIT_APPROVED,
        ).count()
        object_count = base.filter(BomProcurementObject.section == SECTION_OBJECT).count()
        other_leaf = base.filter(BomProcurementObject.section == "other_leaf").count()
        anomaly = base.filter(BomProcurementObject.section == "anomaly").count()
        return {
            "total_count": total,
            "pending_count": pending,
            "approved_count": approved,
            "object_count": object_count,
            "other_leaf_count": other_leaf,
            "anomaly_count": anomaly,
        }

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

    def delete_pending_objects_by_list_id(self, db: Session, list_id: int) -> int:
        count = (
            db.query(BomProcurementObject)
            .filter(
                BomProcurementObject.list_id == list_id,
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_PENDING,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(count)

    def recount_header_from_rows(self, db: Session, header: BomProcurementObjectList) -> None:
        rows = self.list_objects_by_list_id(db, header.id)
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

    def _apply_object_filters(
        self,
        query: Query[BomProcurementObject],
        *,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        section: str | None,
        object_kind: str | None,
        confirm_status: str | None,
        audit_status: str | None,
        part_number: str | None,
        l0_part_number: str | None,
        excel_row: int | None,
    ) -> Query[BomProcurementObject]:
        if location:
            query = query.filter(BomProcurementObjectList.location == location)
        if vehicle_model:
            query = query.filter(BomProcurementObjectList.vehicle_model == vehicle_model)
        if bom_version:
            query = query.filter(BomProcurementObjectList.bom_version == bom_version)
        if section:
            query = query.filter(BomProcurementObject.section == section)
        if object_kind:
            query = query.filter(BomProcurementObject.object_kind == object_kind)
        if confirm_status:
            query = query.filter(BomProcurementObject.confirm_status == confirm_status)
        if audit_status:
            query = query.filter(BomProcurementObject.audit_status == audit_status)
        if part_number:
            query = query.filter(BomProcurementObject.part_number.like(f"%{part_number}%"))
        if l0_part_number:
            query = query.filter(BomProcurementObject.l0_part_number.like(f"%{l0_part_number}%"))
        if excel_row is not None:
            query = query.filter(BomProcurementObject.excel_row == excel_row)
        return query

    @staticmethod
    def _apply_check_order(
        query: Query[BomProcurementObject],
    ) -> Query[BomProcurementObject]:
        """核对顺序：基地 → 车型 → BOM版本 → 原始文件名 → 工作表 → Excel行号。"""
        original_filename = func.coalesce(
            BomProcurementObject.excel_filename,
            BomProcurementObjectList.source_filename,
        )
        return query.order_by(
            BomProcurementObjectList.location,
            BomProcurementObjectList.vehicle_model,
            BomProcurementObjectList.bom_version,
            original_filename,
            BomProcurementObject.excel_sheet_name,
            BomProcurementObject.excel_row,
            BomProcurementObject.id,
        )

    def get_generate_log_by_id(
        self, db: Session, log_id: int
    ) -> BomProcurementObjectGenerateLog | None:
        return (
            db.query(BomProcurementObjectGenerateLog)
            .filter(BomProcurementObjectGenerateLog.id == log_id)
            .first()
        )

    def paginate_generate_logs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomProcurementObjectGenerateLog], int]:
        query = db.query(BomProcurementObjectGenerateLog)
        if location:
            query = query.filter(BomProcurementObjectGenerateLog.location == location)
        if vehicle_model:
            query = query.filter(BomProcurementObjectGenerateLog.vehicle_model == vehicle_model)
        if bom_version:
            query = query.filter(BomProcurementObjectGenerateLog.bom_version == bom_version)
        total = query.count()
        records = (
            query.order_by(BomProcurementObjectGenerateLog.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def create_generate_log(
        self, db: Session, data: BomProcurementObjectGenerateLogWrite
    ) -> BomProcurementObjectGenerateLog:
        record = model_from_payload(BomProcurementObjectGenerateLog, data)
        db.add(record)
        db.flush()
        return record
