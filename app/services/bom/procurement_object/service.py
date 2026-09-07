"""
采购对象清单 — 门面 Service

Router 只依赖本类。生成 / 日志 / 审核下沉到子服务；分类与导出仍是独立模块。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions.base import NotFoundException
from app.repositories.bom.procurement_object_repository import (
    BomProcurementObjectRepository,
    ProcurementObjectListFilters,
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
)
from app.schemas.vo.bom_procurement_object_vo import (
    BomProcurementObjectBatchAuditResultVO,
    BomProcurementObjectBatchDeleteResultVO,
    BomProcurementObjectGenerateLogVO,
    BomProcurementObjectGenerateResultVO,
    BomProcurementObjectListVO,
    BomProcurementObjectPrepStatsVO,
    BomProcurementObjectVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.audit_service import BomProcurementObjectAuditService
from app.services.bom.procurement_object.generate_log_service import (
    BomProcurementObjectGenerateLogService,
)
from app.services.bom.procurement_object.generate_service import (
    BomProcurementObjectGenerateService,
)
from app.services.bom.procurement_object.mapping import to_object_vo
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.vehicle_model import VehicleModelService


class BomProcurementObjectService:
    """采购对象清单门面（查询 + 委托生成 / 日志 / 审核）。"""

    def __init__(self) -> None:
        self.repository = BomProcurementObjectRepository()
        self._generate_service = BomProcurementObjectGenerateService()
        self._generate_log_service = BomProcurementObjectGenerateLogService()
        self._audit_service = BomProcurementObjectAuditService()

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
        locations: list[str] | None = None
        if query.location:
            locations = location_service.expand_for_query(db, query.location)
            if not locations:
                _unused, _models, versions = self.repository.get_filter_options(db)
                filters: ProcurementObjectListFilters = {
                    "locations": location_service.list_registered(db),
                    "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
                    "bom_versions": versions,
                    "summary": {
                        "total_count": 0,
                        "pending_count": 0,
                        "approved_count": 0,
                        "object_count": 0,
                        "other_leaf_count": 0,
                        "anomaly_count": 0,
                    },
                }
                return [], 0, filters
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
            skip=skip,
            limit=query.size,
        )
        _unused, _models, versions = self.repository.get_filter_options(db)
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
        )
        filters = {
            "locations": location_service.list_registered(db),
            "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
            "bom_versions": versions,
            "summary": summary,
        }
        return [to_object_vo(row) for row in rows], total, filters

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
