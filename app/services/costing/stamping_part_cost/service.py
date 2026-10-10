"""
冲压零件价格核算服务（CRUD / 审核门面）

计算逻辑见 app.services.costing.stamping_part_cost.calc。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.models.costing import StampingPartCostCalcLog
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    PartCostListFilters,
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.part.tailor_weld_blank import (
    StampingTailorWeldBlankRepository,
)
from app.schemas.common.deleted_count import DeletedCountVO
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostBatchApproveDTO,
    StampingPartCostBatchReverseAuditDTO,
    StampingPartCostCalcDTO,
    StampingPartCostDeleteDTO,
    StampingPartCostManualUnitCostDTO,
    StampingPartCostQuery,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostBatchAuditResultVO,
    StampingPartCostBatchDeleteResultVO,
    StampingPartCostCalcLogVO,
    StampingPartCostCalcReadyVO,
    StampingPartCostCalcResultVO,
    StampingPartCostVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    TASK_TYPE_STAMPING_PART_COST_CALC,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import (
    WorkerTaskOutcome,
    calc_status_label,
    outcome_from_calc_status,
)
from app.services.costing.stamping_part_cost.audit.service import (
    batch_approve_costs,
    batch_delete_costs,
    batch_reverse_audit_costs,
    update_manual_unit_cost,
)
from app.services.costing.stamping_part_cost.calc.models import ProgressCallback
from app.services.costing.stamping_part_cost.calc.orchestrator.orchestrator import (
    StampingPartCostCalcOrchestrator,
)
from app.services.costing.stamping_part_cost.queries import (
    get_cost_by_id,
    list_suppliers,
    list_years,
    paginate_costs,
)
from app.services.masterdata.vehicle_model.service import VehicleModelService


class StampingPartCostService:
    """冲压零件价格核算：列表/审核 + 计算委托编排器。"""

    def __init__(self) -> None:
        self.cost_repo = StampingPartCostRepository()
        self.steel_repo = SteelPriceRepository()
        self.blank_repo = StampingTailorWeldBlankRepository()
        self.orchestrator = StampingPartCostCalcOrchestrator()

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        month: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> StampingPartCostCalcReadyVO:
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
        dto: StampingPartCostCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingPartCostCalcLog:
        return self.orchestrator.begin_processing(
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
        self.orchestrator.mark_log_failed(db, log_id=log_id, detail_text=detail_text)

    def calculate(
        self,
        db: Session,
        dto: StampingPartCostCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> StampingPartCostCalcResultVO:
        return self.orchestrator.calculate(
            db,
            dto,
            current_user,
            progress_callback=progress_callback,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
        )

    def start_calc(
        self,
        db: Session,
        dto: StampingPartCostCalcDTO,
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
            task_type=TASK_TYPE_STAMPING_PART_COST_CALC,
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
                failed_message=(
                    f"计算失败：成功 {result.success_count}，失败 {result.failed_count}"
                ),
                completed_message=(
                    f"计算{label}：成功 {result.success_count}，" f"失败 {result.failed_count}"
                ),
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
        stamping_supplier: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingPartCostCalcLogVO], int]:
        return self.orchestrator.calc_log_service.list_calc_logs(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            page=page,
            size=size,
        )

    def get_calc_log(self, db: Session, log_id: int) -> StampingPartCostCalcLogVO:
        return self.orchestrator.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        self.orchestrator.calc_log_service.delete_calc_log(db, log_id)

    def delete_all_calc_logs(self, db: Session) -> DeletedCountVO:
        return self.orchestrator.calc_log_service.delete_all_logs(db)

    def paginate(
        self, db: Session, query: StampingPartCostQuery
    ) -> tuple[list[StampingPartCostVO], int, PartCostListFilters]:
        return paginate_costs(self.cost_repo, self.blank_repo, self.steel_repo, db, query)

    def get_by_id(self, db: Session, cost_id: int) -> StampingPartCostVO:
        return get_cost_by_id(self.cost_repo, self.blank_repo, self.steel_repo, db, cost_id)

    def update_manual_unit_cost(
        self,
        db: Session,
        cost_id: int,
        dto: StampingPartCostManualUnitCostDTO,
        current_user: UserVO,
    ) -> StampingPartCostVO:
        return update_manual_unit_cost(
            self.cost_repo,
            self.blank_repo,
            self.steel_repo,
            db,
            cost_id,
            dto,
            current_user,
        )

    def list_years(self, db: Session) -> list[int]:
        return list_years(self.cost_repo, self.steel_repo, db)

    def list_suppliers(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
    ) -> list[str]:
        return list_suppliers(self.cost_repo, db, year=year, month=month, location=location)

    def batch_delete(
        self, db: Session, dto: StampingPartCostDeleteDTO
    ) -> StampingPartCostBatchDeleteResultVO:
        return batch_delete_costs(self.cost_repo, db, dto)

    def batch_approve(
        self,
        db: Session,
        dto: StampingPartCostBatchApproveDTO,
        current_user: UserVO,
    ) -> StampingPartCostBatchAuditResultVO:
        return batch_approve_costs(self.cost_repo, db, dto, current_user)

    def batch_reverse_audit(
        self,
        db: Session,
        dto: StampingPartCostBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> StampingPartCostBatchAuditResultVO:
        return batch_reverse_audit_costs(self.cost_repo, db, dto, current_user)
