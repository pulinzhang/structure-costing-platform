"""
冲压零件价格核算服务（CRUD / 审核门面）

计算逻辑见 app.services.costing.stamping_part_cost.calc。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.costing import StampingPartCostCalcLog
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    PartCostListFilters,
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.tailor_weld_blank_repository import (
    StampingTailorWeldBlankRepository,
)
from app.schemas.common import DeletedCountVO
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
from app.services.costing.stamping_part_cost.audit import (
    batch_approve_costs,
    batch_delete_costs,
    batch_reverse_audit_costs,
    update_manual_unit_cost,
)
from app.services.costing.stamping_part_cost.calc.models import ProgressCallback
from app.services.costing.stamping_part_cost.calc.orchestrator import (
    StampingPartCostCalcOrchestrator,
)
from app.services.costing.stamping_part_cost.calc_ops import (
    begin_processing,
    calculate,
    delete_all_calc_logs,
    delete_calc_log,
    get_calc_log,
    get_calc_ready,
    list_calc_logs,
    mark_log_failed,
    start_calc,
)
from app.services.costing.stamping_part_cost.queries import (
    get_cost_by_id,
    list_locations,
    list_suppliers,
    list_years,
    paginate_costs,
)


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
        return get_calc_ready(
            self,
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
        return begin_processing(self, db, dto, operator_id=operator_id, operator_name=operator_name)

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        mark_log_failed(self, db, log_id=log_id, detail_text=detail_text)

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
        return calculate(
            self,
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
        return start_calc(self, db, dto, current_user)

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
        return list_calc_logs(
            self,
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            page=page,
            size=size,
        )

    def get_calc_log(self, db: Session, log_id: int) -> StampingPartCostCalcLogVO:
        return get_calc_log(self, db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        delete_calc_log(self, db, log_id)

    def delete_all_calc_logs(self, db: Session) -> DeletedCountVO:
        return delete_all_calc_logs(self, db)

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

    def list_locations(self, db: Session, year: int | None = None) -> list[str]:
        return list_locations(db, year)

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
