"""
BOM 焊接工艺拆解 — 门面 Service

对外统一入口：查询 / 修改 / 生成 / 审核。
复杂逻辑下沉到 generate / audit / query / lines。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.bom import BomWeldingProcessBreakdownGenerateLog
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
    WeldingBreakdownListFilters,
)
from app.schemas.common.deleted_count import DeletedCountVO
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownBatchApproveDTO,
    BomWeldingProcessBreakdownBatchReverseAuditDTO,
    BomWeldingProcessBreakdownGenerateDTO,
    BomWeldingProcessBreakdownLineUpdateDTO,
    BomWeldingProcessBreakdownNodeLinesUpdateDTO,
    BomWeldingProcessBreakdownQuery,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    BomWeldingProcessBreakdownBatchAuditResultVO,
    BomWeldingProcessBreakdownBatchDeleteResultVO,
    BomWeldingProcessBreakdownGenerateLogVO,
    BomWeldingProcessBreakdownGeneratePrepStatsVO,
    BomWeldingProcessBreakdownGenerateResultVO,
    BomWeldingProcessBreakdownLineVO,
    BomWeldingProcessBreakdownNodeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_process_breakdown.audit.service import (
    BomWeldingProcessBreakdownAuditService,
)
from app.services.bom.welding_process_breakdown.generate.log import (
    BomWeldingProcessBreakdownGenerateLogService,
)
from app.services.bom.welding_process_breakdown.generate.service import (
    BomWeldingProcessBreakdownGenerateService,
    ProgressCallback,
)
from app.services.bom.welding_process_breakdown.generate.task import start_generate
from app.services.bom.welding_process_breakdown.lines import (
    update_line,
    update_node_lines,
)
from app.services.bom.welding_process_breakdown.query import (
    get_node,
    paginate_nodes,
)
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.settings.foreign_key.service import ensure_deletable


class BomWeldingProcessBreakdownService:
    """焊接工艺拆解门面（Router 只依赖本类）"""

    def __init__(self) -> None:
        self.repository = BomWeldingProcessBreakdownRepository()
        self.node_repository = BomNodeRepository()
        self._generate_service = BomWeldingProcessBreakdownGenerateService()
        self._generate_log_service = BomWeldingProcessBreakdownGenerateLogService()
        self._audit_service = BomWeldingProcessBreakdownAuditService()

    def paginate(
        self, db: Session, query: BomWeldingProcessBreakdownQuery
    ) -> tuple[list[BomWeldingProcessBreakdownNodeVO], int, WeldingBreakdownListFilters]:
        return paginate_nodes(
            self.repository,
            db,
            query,
            location_service=LocationService(),
            vehicle_service=VehicleModelService(),
        )

    def get_node(self, db: Session, node_id: int) -> BomWeldingProcessBreakdownNodeVO:
        return get_node(self.repository, self.node_repository, db, node_id)

    def get_generate_prep_stats(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomWeldingProcessBreakdownGeneratePrepStatsVO:
        return self._generate_service.get_prep_stats(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def generate_from_bom(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownGenerateDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
        started_at: datetime | None = None,
    ) -> BomWeldingProcessBreakdownGenerateResultVO:
        return self._generate_service.generate(
            db,
            dto,
            current_user,
            progress_callback=progress_callback,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
            started_at=started_at,
        )

    def copy_for_new_tree(
        self,
        db: Session,
        *,
        snapshot_id: int,
        source_id_remap: dict[int, int],
        current_user: UserVO,
    ) -> list[int]:
        """工程变更种树后：从旧树拆解结果抄到新树（不 commit）。"""
        return self._generate_service.copy_for_new_tree(
            db,
            snapshot_id=snapshot_id,
            source_id_remap=source_id_remap,
            current_user=current_user,
        )

    def begin_generate_processing(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        customer_name: str | None = None,
        operator_id: int | None = None,
        operator_name: str | None = None,
    ) -> BomWeldingProcessBreakdownGenerateLog:
        return self._generate_log_service.begin_processing(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            customer_name=customer_name,
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def list_generate_logs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[BomWeldingProcessBreakdownGenerateLogVO], int]:
        return self._generate_log_service.list_logs(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            page=page,
            size=size,
        )

    def get_generate_log(self, db: Session, log_id: int) -> BomWeldingProcessBreakdownGenerateLogVO:
        return self._generate_log_service.get_log(db, log_id)

    def delete_generate_log(self, db: Session, log_id: int) -> None:
        self._generate_log_service.delete_log(db, log_id)

    def delete_all_generate_logs(self, db: Session) -> DeletedCountVO:
        return self._generate_log_service.delete_all_logs(db)

    def mark_generate_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        message: str,
        detail_text: str | None = None,
    ) -> None:
        self._generate_service.mark_log_failed(
            db, log_id=log_id, message=message, detail_text=detail_text
        )

    def start_generate(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownGenerateDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        return start_generate(self, db, dto, current_user)

    def update_line(
        self,
        db: Session,
        line_id: int,
        dto: BomWeldingProcessBreakdownLineUpdateDTO,
        current_user: UserVO,
    ) -> BomWeldingProcessBreakdownLineVO:
        return update_line(self.repository, db, line_id, dto, current_user)

    def update_node_lines(
        self,
        db: Session,
        node_id: int,
        dto: BomWeldingProcessBreakdownNodeLinesUpdateDTO,
        current_user: UserVO,
    ) -> BomWeldingProcessBreakdownNodeVO:
        return update_node_lines(
            self.repository, self.node_repository, db, node_id, dto, current_user
        )

    def batch_delete(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomWeldingProcessBreakdownBatchDeleteResultVO:
        return self._audit_service.batch_delete(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def batch_approve(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownBatchApproveDTO,
        current_user: UserVO,
    ) -> BomWeldingProcessBreakdownBatchAuditResultVO:
        return self._audit_service.batch_approve(db, dto, current_user)

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomWeldingProcessBreakdownBatchAuditResultVO:
        return self._audit_service.batch_reverse_audit(db, dto, current_user)

    def delete_node_for_engineering_change_rollback(self, db: Session, node_id: int) -> None:
        """工程变更回滚：删未审拆解节点；已审则 409。只 flush。"""
        from app.common.audit import AUDIT_APPROVED
        from app.common.engineering_change_gates import EC_ROLLBACK_BLOCKED
        from app.exceptions.base import BusinessException

        row = self.repository.get_node_by_id(db, node_id)
        if row is None:
            return
        if row.audit_status == AUDIT_APPROVED:
            raise BusinessException(EC_ROLLBACK_BLOCKED, code=409)
        ensure_deletable(
            db,
            "bom_welding_process_breakdown_node",
            [{"id": node_id}],
            subject="该焊接工艺拆解",
        )
        self.repository.delete_node_by_id(db, node_id)
