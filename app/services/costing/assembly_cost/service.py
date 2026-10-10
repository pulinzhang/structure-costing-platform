"""成品月核价 — Service 门面（列表/审核 + 计算委托）。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.exceptions.base import NotFoundException
from app.models.costing.assembly_cost_calc_log import AssemblyCostCalcLog
from app.repositories.bom.annual_part_price_repository import (
    BomAnnualPartPriceRepository,
)
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.costing.assembly_cost.assembly_cost_repository import (
    AssemblyCostListFilters,
    AssemblyCostRepository,
    empty_assembly_cost_summary,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.schemas.common.deleted_count import DeletedCountVO
from app.schemas.dto.assembly_cost_dto import (
    AssemblyCostBatchApproveDTO,
    AssemblyCostBatchDeleteDTO,
    AssemblyCostBatchReverseDTO,
    AssemblyCostCalcDTO,
    AssemblyCostQuery,
)
from app.schemas.vo.assembly_cost_vo import (
    AssemblyCostBatchResultVO,
    AssemblyCostCalcLogVO,
    AssemblyCostCalcReadyVO,
    AssemblyCostCalcResultVO,
    AssemblyCostVO,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    TASK_TYPE_ASSEMBLY_COST_CALC,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import (
    ProgressCallback,
    WorkerTaskOutcome,
    calc_status_label,
    outcome_from_calc_status,
)
from app.services.costing.assembly_cost.audit.service import (
    batch_approve_costs,
    batch_delete_costs,
    batch_reverse_costs,
)
from app.services.costing.assembly_cost.calc.calc_log import (
    DUPLICATE_SCOPE_CALC_MESSAGE,
    AssemblyCostCalcLogService,
    DuplicateScopeCalcError,
)
from app.services.costing.assembly_cost.calc.orchestrator.orchestrator import (
    AssemblyCostCalcOrchestrator,
)
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.service import VehicleModelService

__all__ = [
    "DUPLICATE_SCOPE_CALC_MESSAGE",
    "AssemblyCostService",
    "DuplicateScopeCalcError",
]


class AssemblyCostService:
    """成品月核价：列表/审核 + 计算委托编排器。"""

    def __init__(self) -> None:
        self.cost_repo = AssemblyCostRepository()
        self.stamping_cost_repo = StampingPartCostRepository()
        self.annual_price_repo = BomAnnualPartPriceRepository()
        self.welding_fee_repo = BomWeldingFeeRepository()
        self.packaging_fee_repo = BomPackagingTransportFeeRepository()
        self.procurement_object_repo = BomProcurementObjectRepository()
        self.orchestrator = AssemblyCostCalcOrchestrator()
        self.calc_log_service = AssemblyCostCalcLogService()

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
    ) -> AssemblyCostCalcReadyVO:
        return self.orchestrator.get_calc_ready(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
        )

    def begin_processing(
        self,
        db: Session,
        dto: AssemblyCostCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> AssemblyCostCalcLog:
        return self.calc_log_service.begin_processing(
            db,
            dto,
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        self.calc_log_service.mark_log_failed(db, log_id=log_id, detail_text=detail_text)

    def calculate(
        self,
        db: Session,
        dto: AssemblyCostCalcDTO,
        *,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> AssemblyCostCalcResultVO:
        return self.orchestrator.calculate(
            db,
            dto,
            current_user=current_user,
            progress_callback=progress_callback,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
        )

    def start_calc(
        self,
        db: Session,
        dto: AssemblyCostCalcDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        canonical, vehicle_model = VehicleModelService().require_introducible(
            db, dto.location, dto.vehicle_model, dto.year, dto.month
        )
        dto = dto.model_copy(update={"location": canonical, "vehicle_model": vehicle_model})
        lock_log = self.begin_processing(
            db,
            dto,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
        log_id = lock_log.id
        calc_batch_id = lock_log.calc_batch_id
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_ASSEMBLY_COST_CALC,
            message="已提交计算队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            result = self.calculate(
                worker_db,
                dto,
                current_user=current_user,
                progress_callback=on_progress,
                log_id=log_id,
                calc_batch_id=calc_batch_id,
            )
            label = calc_status_label(result.status)
            return outcome_from_calc_status(
                result.status,
                failed_message=result.message or "计算失败",
                completed_message=f"计算{label}：{result.message or ''}",
                result=result.model_dump(),
            )

        def on_crash(worker_db: Session, error: BaseException) -> None:
            self.mark_log_failed(
                worker_db,
                log_id=log_id,
                detail_text=f"计算失败: {error}",
            )

        async_task_service.submit_session_worker(
            task.task_id,
            start_message="后台开始计算...",
            work=work,
            on_crash=on_crash,
        )
        return AsyncTaskAcceptedVO(task_id=task.task_id)

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[AssemblyCostCalcLogVO], int]:
        skip = max(page - 1, 0) * max(size, 1)
        return self.calc_log_service.list_calc_logs(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            skip=skip,
            limit=size,
        )

    def get_calc_log(self, db: Session, log_id: int) -> AssemblyCostCalcLogVO:
        return self.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        self.calc_log_service.delete_calc_log(db, log_id)

    def delete_all_calc_logs(self, db: Session) -> DeletedCountVO:
        return self.calc_log_service.delete_all_logs(db)

    def list_years(self, db: Session) -> list[int]:
        """计算页年度：取上游价表并集（从未核算过也能选）。

        来源：冲压零件价 / 年度零件价 / 成品焊接费 / 包装运输费。
        不含「仅出现在成品核价结果表」的年份——那是结果筛选，不是计算前置。
        """
        years: set[int] = set()
        years.update(self.stamping_cost_repo.get_distinct_years(db))
        years.update(self.annual_price_repo.get_distinct_years(db))
        years.update(self.welding_fee_repo.get_distinct_years(db))
        years.update(self.packaging_fee_repo.get_distinct_years(db))
        return sorted(years, reverse=True)

    def paginate(
        self, db: Session, query: AssemblyCostQuery
    ) -> tuple[list[AssemblyCostVO], int, AssemblyCostListFilters]:
        locations: list[str] | None = None
        if query.location:
            locations = LocationService().expand_for_query(db, query.location)
            if not locations:
                empty_filters: AssemblyCostListFilters = {
                    "year": query.year,
                    "month": query.month,
                    "location": query.location,
                    "vehicle_model": query.vehicle_model,
                    "bom_version": query.bom_version,
                    "part_number": query.part_number,
                    "audit_status": query.audit_status,
                    "calc_status": query.calc_status,
                    "view": query.view,
                    "level": query.level,
                    "object_kind": query.object_kind,
                    "summary": empty_assembly_cost_summary(),
                }
                return [], 0, empty_filters
        rows, total, filters = self.cost_repo.paginate(
            db,
            year=query.year,
            month=query.month,
            locations=locations,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            part_number=query.part_number,
            audit_status=query.audit_status,
            calc_status=query.calc_status,
            view=query.view,
            level=query.level,
            object_kind=query.object_kind,
            confirm_status=query.confirm_status,
            skip=(query.page - 1) * query.size,
            limit=query.size,
        )
        vos = [AssemblyCostVO.model_validate(r) for r in rows]
        object_ids = [vo.procurement_object_id for vo in vos if vo.procurement_object_id]
        confirm_map = self.procurement_object_repo.map_confirm_status_by_ids(db, object_ids)
        attached: list[AssemblyCostVO] = []
        for vo in vos:
            if vo.procurement_object_id is None:
                attached.append(vo)
                continue
            status = confirm_map.get(vo.procurement_object_id)
            if status is None:
                attached.append(vo)
            else:
                attached.append(vo.model_copy(update={"confirm_status": status}))
        return attached, total, filters

    def get_by_id(self, db: Session, cost_id: int) -> AssemblyCostVO:
        row = self.cost_repo.get_by_id(db, cost_id)
        if row is None:
            raise NotFoundException("记录不存在")
        return AssemblyCostVO.model_validate(row)

    def batch_delete(
        self,
        db: Session,
        dto: AssemblyCostBatchDeleteDTO,
    ) -> AssemblyCostBatchResultVO:
        return batch_delete_costs(self.cost_repo, db, dto)

    def batch_approve(
        self,
        db: Session,
        dto: AssemblyCostBatchApproveDTO,
        *,
        current_user: UserVO,
    ) -> AssemblyCostBatchResultVO:
        return batch_approve_costs(self.cost_repo, db, dto, current_user)

    def batch_reverse(
        self,
        db: Session,
        dto: AssemblyCostBatchReverseDTO,
        *,
        current_user: UserVO,
    ) -> AssemblyCostBatchResultVO:
        return batch_reverse_costs(self.cost_repo, db, dto, current_user)
