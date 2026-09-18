"""
采购对象清单 — 门面 Service

Router 只依赖本类。生成 / 日志 / 审核下沉到子服务；分类与导出仍是独立模块。
"""

from __future__ import annotations

from typing import TypedDict

from sqlalchemy.orm import Session

from app.common.period import resolve_as_of_month
from app.exceptions.base import NotFoundException
from app.repositories.bom.procurement_object_repository import (
    BomProcurementObjectRepository,
    ProcurementObjectAuditSummary,
    empty_procurement_object_summary,
)
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectBatchApproveDTO,
    BomProcurementObjectBatchDeleteDTO,
    BomProcurementObjectBatchReverseAuditDTO,
    BomProcurementObjectConfirmDTO,
    BomProcurementObjectGenerateDTO,
    BomProcurementObjectGenerateLogQuery,
    BomProcurementObjectPrepQuery,
    BomProcurementObjectQuery,
    BomProcurementObjectSupplierChoiceQuery,
    BomProcurementObjectSupplierDTO,
)
from app.schemas.vo.bom_procurement_object_vo import (
    BomProcurementObjectBatchAuditResultVO,
    BomProcurementObjectBatchDeleteResultVO,
    BomProcurementObjectGenerateLogVO,
    BomProcurementObjectGenerateResultVO,
    BomProcurementObjectListVO,
    BomProcurementObjectPrepStatsVO,
    BomProcurementObjectSupplierUploadResultVO,
    BomProcurementObjectVO,
)
from app.schemas.vo.supplier_vo import SupplierChoiceVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.audit_service import BomProcurementObjectAuditService
from app.services.bom.procurement_object.generate_log_service import (
    BomProcurementObjectGenerateLogService,
)
from app.services.bom.procurement_object.generate_service import (
    BomProcurementObjectGenerateService,
)
from app.services.bom.procurement_object.insert_service import BomProcurementObjectInsertService
from app.services.bom.procurement_object.mapping import to_object_vo
from app.services.bom.procurement_object.supplier_upload_service import (
    BomProcurementObjectSupplierUploadService,
)
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.supplier import SupplierService
from app.services.masterdata.vehicle_model import VehicleModelService


class ProcurementObjectListFilters(TypedDict):
    """列表筛选项（Service 组装）。供应商点选走独立检索，不塞进本结构。"""

    locations: list[str]
    vehicle_models: list[str]
    bom_versions: list[str]
    summary: ProcurementObjectAuditSummary


class BomProcurementObjectService:
    """采购对象清单门面（查询 + 委托生成 / 日志 / 审核）。"""

    def __init__(self) -> None:
        self.repository = BomProcurementObjectRepository()
        self._generate_service = BomProcurementObjectGenerateService()
        self._insert_service = BomProcurementObjectInsertService()
        self._generate_log_service = BomProcurementObjectGenerateLogService()
        self._audit_service = BomProcurementObjectAuditService()
        self._supplier_upload_service = BomProcurementObjectSupplierUploadService()

    def prep_stats(
        self, db: Session, query: BomProcurementObjectPrepQuery
    ) -> BomProcurementObjectPrepStatsVO:
        return self._generate_service.prep_stats(db, query)

    def generate(
        self,
        db: Session,
        dto: BomProcurementObjectGenerateDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectGenerateResultVO:
        return self._generate_service.generate(db, dto, current_user)

    def insert_for_new_tree(
        self,
        db: Session,
        *,
        snapshot_id: int,
        new_l0_id: int,
        old_l0_id: int | None,
        current_user: UserVO,
    ) -> list[int]:
        """合册种树后插本树采购对象行（不 commit）。"""
        return self._insert_service.insert_for_new_tree(
            db,
            snapshot_id=snapshot_id,
            new_l0_id=new_l0_id,
            old_l0_id=old_l0_id,
            current_user=current_user,
        )

    def list_generate_logs(
        self,
        db: Session,
        query: BomProcurementObjectGenerateLogQuery,
    ) -> tuple[list[BomProcurementObjectGenerateLogVO], int]:
        return self._generate_log_service.list_logs(db, query)

    def get_generate_log(self, db: Session, log_id: int) -> BomProcurementObjectGenerateLogVO:
        return self._generate_log_service.get_log(db, log_id)

    def get_summary(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomProcurementObjectListVO:
        header = self.repository.get_list_by_scope(
            db,
            location=location.strip(),
            vehicle_model=vehicle_model.strip(),
            bom_version=bom_version.strip(),
        )
        if header is None:
            raise NotFoundException("尚未生成采购对象清单")
        return BomProcurementObjectListVO.model_validate(header)

    def paginate(
        self, db: Session, query: BomProcurementObjectQuery
    ) -> tuple[list[BomProcurementObjectVO], int, ProcurementObjectListFilters]:
        skip = (query.page - 1) * query.size
        location_service = LocationService()
        supplier_service = SupplierService()
        locations: list[str] | None = None
        supplier_names: list[str] | None = supplier_service.names_for_query(db, query.supplier_name)
        empty_supplier = supplier_names is not None and not supplier_names
        as_of_year: int | None = None
        as_of_month: int | None = None
        if not query.include_expired:
            as_of_year, as_of_month = resolve_as_of_month(query.year, query.month)
        if query.location:
            locations = location_service.expand_for_query(db, query.location)
            if not locations:
                return [], 0, self._list_filters(db, location_service, query, empty=True)
        if empty_supplier:
            return [], 0, self._list_filters(db, location_service, query, empty=True)
        rows, total = self.repository.paginate_objects(
            db,
            locations=locations,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            section=query.section,
            object_kind=query.object_kind,
            confirm_status=query.confirm_status,
            audit_status=query.audit_status,
            part_number=query.part_number,
            l0_part_number=query.l0_part_number,
            excel_row=query.excel_row,
            supplier_names=supplier_names,
            has_supplier=query.has_supplier,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
            skip=skip,
            limit=query.size,
        )
        filters = self._list_filters(
            db,
            location_service,
            query,
            empty=False,
            locations=locations,
        )
        return [to_object_vo(row) for row in rows], total, filters

    def _list_filters(
        self,
        db: Session,
        location_service: LocationService,
        query: BomProcurementObjectQuery,
        *,
        empty: bool,
        locations: list[str] | None = None,
    ) -> ProcurementObjectListFilters:
        _unused, _models, versions = self.repository.get_filter_options(db)
        if empty:
            summary: ProcurementObjectAuditSummary = empty_procurement_object_summary()
        else:
            supplier_names = SupplierService().names_for_query(db, query.supplier_name)
            as_of_year: int | None = None
            as_of_month: int | None = None
            if not query.include_expired:
                as_of_year, as_of_month = resolve_as_of_month(query.year, query.month)
            summary = self.repository.summarize_objects(
                db,
                locations=locations,
                vehicle_model=query.vehicle_model,
                bom_version=query.bom_version,
                section=query.section,
                object_kind=query.object_kind,
                confirm_status=query.confirm_status,
                audit_status=query.audit_status,
                part_number=query.part_number,
                l0_part_number=query.l0_part_number,
                excel_row=query.excel_row,
                supplier_names=supplier_names,
                has_supplier=query.has_supplier,
                as_of_year=as_of_year,
                as_of_month=as_of_month,
            )
        return {
            "locations": location_service.list_registered(db),
            "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
            "bom_versions": versions,
            "summary": summary,
        }

    def search_supplier_choices(
        self,
        db: Session,
        query: BomProcurementObjectSupplierChoiceQuery,
    ) -> tuple[list[SupplierChoiceVO], int]:
        return SupplierService().search_enabled_choices(
            db,
            keyword=query.q,
            page=query.page,
            size=query.size,
        )

    def build_supplier_template(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> tuple[bytes, str]:
        return self._supplier_upload_service.build_template(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def upload_suppliers(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        filename: str,
        file_content: bytes,
        current_user: UserVO,
    ) -> BomProcurementObjectSupplierUploadResultVO:
        return self._supplier_upload_service.process_upload(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            filename=filename,
            file_content=file_content,
            current_user=current_user,
        )

    def get_by_id(self, db: Session, object_id: int) -> BomProcurementObjectVO:
        row = self.repository.get_object_by_id(db, object_id)
        if row is None:
            raise NotFoundException(f"采购对象不存在: id={object_id}")
        return to_object_vo(row)

    def confirm(
        self,
        db: Session,
        object_id: int,
        dto: BomProcurementObjectConfirmDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectVO:
        return self._audit_service.confirm(db, object_id, dto, current_user)

    def update_supplier(
        self,
        db: Session,
        object_id: int,
        dto: BomProcurementObjectSupplierDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectVO:
        return self._audit_service.update_supplier(db, object_id, dto, current_user)

    def batch_approve(
        self,
        db: Session,
        dto: BomProcurementObjectBatchApproveDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectBatchAuditResultVO:
        return self._audit_service.batch_approve(db, dto, current_user)

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomProcurementObjectBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectBatchAuditResultVO:
        return self._audit_service.batch_reverse_audit(db, dto, current_user)

    def batch_delete(
        self,
        db: Session,
        dto: BomProcurementObjectBatchDeleteDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectBatchDeleteResultVO:
        return self._audit_service.batch_delete(db, dto, current_user)

    def get_list_id_by_snapshot(self, db: Session, snapshot_id: int) -> int | None:
        """工程变更：snapshot 上是否已有采购对象清单头。"""
        header = self.repository.get_list_by_snapshot_id(db, snapshot_id)
        return header.id if header is not None else None

    def delete_object_for_engineering_change_rollback(self, db: Session, object_id: int) -> None:
        """工程变更回滚：删未审对象行；已审则 409。只 flush。"""
        from app.common.audit import AUDIT_APPROVED
        from app.common.engineering_change_gates import EC_ROLLBACK_BLOCKED
        from app.exceptions.base import BusinessException

        row = self.repository.get_object_by_id(db, object_id)
        if row is None:
            return
        if row.audit_status == AUDIT_APPROVED:
            raise BusinessException(EC_ROLLBACK_BLOCKED, code=409)
        list_id = row.list_id
        self.repository.delete_object(db, row)
        header = self.repository.get_list_by_id(db, list_id)
        if header is not None:
            self.repository.recount_header_from_rows(db, header)

    def delete_list_if_empty_for_engineering_change_rollback(
        self, db: Session, list_id: int
    ) -> None:
        """工程变更回滚：头下无行则删头。只 flush。"""
        header = self.repository.get_list_by_id(db, list_id)
        if header is None:
            return
        objects = self.repository.list_objects_by_list_id(db, header.id)
        if objects:
            return
        self.repository.delete_list(db, header)
