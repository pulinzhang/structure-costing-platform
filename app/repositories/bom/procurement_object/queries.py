"""采购对象清单查询：清单/对象、分页、导出、HUD、生成日志。"""

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom.procurement_object import (
    BomProcurementObject,
    BomProcurementObjectList,
)
from app.models.bom.procurement_object_generate_log import BomProcurementObjectGenerateLog
from app.repositories.bom.procurement_object.types import (
    KIND_L0_DEGENERATE,
    SECTION_OBJECT,
    ProcurementObjectAuditSummary,
    count_matching,
)


class BomProcurementObjectQueries:
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

    def list_lists_by_location_vehicle(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[BomProcurementObjectList]:
        return (
            db.query(BomProcurementObjectList)
            .filter(
                BomProcurementObjectList.location == location,
                BomProcurementObjectList.vehicle_model == vehicle_model,
            )
            .order_by(BomProcurementObjectList.id.asc())
            .all()
        )

    def list_objects_by_location_vehicle(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[BomProcurementObject]:
        objects: list[BomProcurementObject] = []
        for header in self.list_lists_by_location_vehicle(
            db, location=location, vehicle_model=vehicle_model
        ):
            objects.extend(self.list_objects_by_list_id(db, header.id))
        return objects

    def get_latest_list(self, db: Session) -> BomProcurementObjectList | None:
        return (
            db.query(BomProcurementObjectList)
            .order_by(
                BomProcurementObjectList.generated_at.desc(),
                BomProcurementObjectList.id.desc(),
            )
            .first()
        )

    def get_object_by_id(self, db: Session, object_id: int) -> BomProcurementObject | None:
        return db.query(BomProcurementObject).filter(BomProcurementObject.id == object_id).first()

    def get_confirm_status_by_id(self, db: Session, object_id: int) -> str | None:
        obj = self.get_object_by_id(db, object_id)
        if obj is None:
            return None
        return obj.confirm_status

    def map_confirm_status_by_ids(self, db: Session, object_ids: list[int]) -> dict[int, str]:
        unique_ids = [item for item in object_ids if item is not None]
        if not unique_ids:
            return {}
        rows = (
            db.query(BomProcurementObject.id, BomProcurementObject.confirm_status)
            .filter(BomProcurementObject.id.in_(unique_ids))
            .all()
        )
        return {int(row_id): status for row_id, status in rows}

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

    def paginate_objects(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        section: str | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
        audit_status: str | None = None,
        part_number: str | None = None,
        l0_part_number: str | None = None,
        excel_row: int | None = None,
        supplier_names: list[str] | None = None,
        has_supplier: bool | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomProcurementObject], int]:
        query = self._apply_object_filters(
            db.query(BomProcurementObject).join(BomProcurementObjectList),
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            section=section,
            object_kind=object_kind,
            confirm_status=confirm_status,
            audit_status=audit_status,
            part_number=part_number,
            l0_part_number=l0_part_number,
            excel_row=excel_row,
            supplier_names=supplier_names,
            has_supplier=has_supplier,
        )
        total = query.count()
        rows = self._apply_check_order(query).offset(skip).limit(limit).all()
        return rows, total

    def list_objects_for_export(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        section: str | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
        audit_status: str | None = None,
        part_number: str | None = None,
        l0_part_number: str | None = None,
        excel_row: int | None = None,
        supplier_names: list[str] | None = None,
        has_supplier: bool | None = None,
    ) -> list[BomProcurementObject]:
        query = self._apply_object_filters(
            db.query(BomProcurementObject).join(BomProcurementObjectList),
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            section=section,
            object_kind=object_kind,
            confirm_status=confirm_status,
            audit_status=audit_status,
            part_number=part_number,
            l0_part_number=l0_part_number,
            excel_row=excel_row,
            supplier_names=supplier_names,
            has_supplier=has_supplier,
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
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        section: str | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
        audit_status: str | None = None,
        part_number: str | None = None,
        l0_part_number: str | None = None,
        excel_row: int | None = None,
        supplier_names: list[str] | None = None,
        has_supplier: bool | None = None,
    ) -> ProcurementObjectAuditSummary:
        base = self._apply_object_filters(
            db.query(BomProcurementObject).join(BomProcurementObjectList),
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            section=section,
            object_kind=object_kind,
            confirm_status=confirm_status,
            audit_status=audit_status,
            part_number=part_number,
            l0_part_number=l0_part_number,
            excel_row=excel_row,
            supplier_names=supplier_names,
            has_supplier=has_supplier,
        )
        row = base.with_entities(
            func.count(BomProcurementObject.id).label("total_count"),
            count_matching(
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_PENDING,
            ).label("pending_count"),
            count_matching(
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_APPROVED,
            ).label("approved_count"),
            count_matching(BomProcurementObject.section == SECTION_OBJECT).label("object_count"),
            count_matching(
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.object_kind == KIND_L0_DEGENERATE,
            ).label("object_l0_degenerate_count"),
            count_matching(BomProcurementObject.section == "other_leaf").label("other_leaf_count"),
            count_matching(BomProcurementObject.section == "anomaly").label("anomaly_count"),
        ).one()
        return {
            "total_count": int(row.total_count or 0),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
            "object_count": int(row.object_count or 0),
            "object_l0_degenerate_count": int(row.object_l0_degenerate_count or 0),
            "other_leaf_count": int(row.other_leaf_count or 0),
            "anomaly_count": int(row.anomaly_count or 0),
        }

    def _apply_object_filters(
        self,
        query: Query[BomProcurementObject],
        *,
        location: str | None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
        bom_version: str | None,
        section: str | None,
        object_kind: str | None,
        confirm_status: str | None,
        audit_status: str | None,
        part_number: str | None,
        l0_part_number: str | None,
        excel_row: int | None,
        supplier_names: list[str] | None = None,
        has_supplier: bool | None = None,
    ) -> Query[BomProcurementObject]:
        if locations is not None:
            query = query.filter(BomProcurementObjectList.location.in_(locations))
        elif location:
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
        if supplier_names is not None:
            query = query.filter(BomProcurementObject.supplier_name.in_(supplier_names))
        if has_supplier is True:
            query = query.filter(BomProcurementObject.supplier_name.isnot(None))
        elif has_supplier is False:
            query = query.filter(BomProcurementObject.supplier_name.is_(None))
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
