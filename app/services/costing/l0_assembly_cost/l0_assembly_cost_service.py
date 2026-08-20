"""成品月核价 — Service 门面（列表/审核 + 计算委托）。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.timezone import now
from app.models.costing.l0_assembly_cost_calc_log import L0AssemblyCostCalcLog
from app.repositories.bom.annual_part_price_repository import (
    BomAnnualPartPriceRepository,
)
from app.repositories.bom.l0_welding_fee_repository import BomL0WeldingFeeRepository
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.repositories.costing.l0_assembly_cost.l0_assembly_cost_repository import (
    L0AssemblyCostListFilters,
    L0AssemblyCostRepository,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.schemas.dto.l0_assembly_cost_dto import (
    L0AssemblyCostBatchApproveDTO,
    L0AssemblyCostBatchDeleteDTO,
    L0AssemblyCostBatchReverseDTO,
    L0AssemblyCostCalcDTO,
    L0AssemblyCostQuery,
)
from app.schemas.vo.l0_assembly_cost_vo import (
    L0AssemblyCostBatchResultVO,
    L0AssemblyCostCalcLogVO,
    L0AssemblyCostCalcReadyVO,
    L0AssemblyCostCalcResultVO,
    L0AssemblyCostVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.l0_assembly_cost.calc.calc_log_service import (
    DUPLICATE_SCOPE_CALC_MESSAGE,
    DuplicateScopeCalcError,
    L0AssemblyCostCalcLogService,
)
from app.services.costing.l0_assembly_cost.calc.orchestrator import (
    L0AssemblyCostCalcOrchestrator,
    ProgressCallback,
)

__all__ = [
    "DUPLICATE_SCOPE_CALC_MESSAGE",
    "DuplicateScopeCalcError",
    "L0AssemblyCostService",
]


class L0AssemblyCostService:
    """成品月核价：列表/审核 + 计算委托编排器。"""

    def __init__(self) -> None:
        self.cost_repo = L0AssemblyCostRepository()
        self.stamping_cost_repo = StampingPartCostRepository()
        self.annual_price_repo = BomAnnualPartPriceRepository()
        self.welding_fee_repo = BomL0WeldingFeeRepository()
        self.packaging_fee_repo = BomPackagingTransportFeeRepository()
        self.orchestrator = L0AssemblyCostCalcOrchestrator()
        self.calc_log_service = L0AssemblyCostCalcLogService()

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> L0AssemblyCostCalcReadyVO:
        return self.orchestrator.get_calc_ready(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def begin_processing(
        self,
        db: Session,
        dto: L0AssemblyCostCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> L0AssemblyCostCalcLog:
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
        self.calc_log_service.mark_log_failed(
            db, log_id=log_id, detail_text=detail_text
        )

    def calculate(
        self,
        db: Session,
        dto: L0AssemblyCostCalcDTO,
        *,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> L0AssemblyCostCalcResultVO:
        return self.orchestrator.calculate(
            db,
            dto,
            current_user=current_user,
            progress_callback=progress_callback,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
        )

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
    ) -> tuple[list[L0AssemblyCostCalcLogVO], int]:
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

    def get_calc_log(
        self, db: Session, log_id: int
    ) -> L0AssemblyCostCalcLogVO | None:
        return self.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> bool:
        return self.calc_log_service.delete_calc_log(db, log_id)

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
        self, db: Session, query: L0AssemblyCostQuery
    ) -> tuple[list[L0AssemblyCostVO], int, L0AssemblyCostListFilters]:
        rows, total, filters = self.cost_repo.paginate(
            db,
            year=query.year,
            month=query.month,
            location=query.location,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            part_number=query.part_number,
            audit_status=query.audit_status,
            calc_status=query.calc_status,
            skip=query.skip,
            limit=query.limit,
        )
        return (
            [L0AssemblyCostVO.model_validate(r) for r in rows],
            total,
            filters,
        )

    def get_by_id(self, db: Session, cost_id: int) -> L0AssemblyCostVO | None:
        row = self.cost_repo.get_by_id(db, cost_id)
        if row is None:
            return None
        return L0AssemblyCostVO.model_validate(row)

    def batch_delete(
        self,
        db: Session,
        dto: L0AssemblyCostBatchDeleteDTO,
        *,
        current_user: UserVO,
    ) -> L0AssemblyCostBatchResultVO:
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        bom_version = dto.bom_version.strip()
        skipped = self.cost_repo.count_approved_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        count = self.cost_repo.delete_unaudited_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        db.commit()
        message = f"已删除 {count} 条"
        if skipped:
            message += f"，跳过已审核 {skipped} 条"
        return L0AssemblyCostBatchResultVO(
            affected_count=count,
            skipped_count=skipped,
            message=message,
        )

    def batch_approve(
        self,
        db: Session,
        dto: L0AssemblyCostBatchApproveDTO,
        *,
        current_user: UserVO,
    ) -> L0AssemblyCostBatchResultVO:
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        bom_version = dto.bom_version.strip()
        count = self.cost_repo.approve_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            audited_by=display_name(current_user),
            audited_at=now(),
            audit_remark=dto.audit_remark,
        )
        db.commit()
        return L0AssemblyCostBatchResultVO(
            affected_count=count,
            skipped_count=0,
            message=f"已审核通过 {count} 条",
        )

    def batch_reverse(
        self,
        db: Session,
        dto: L0AssemblyCostBatchReverseDTO,
        *,
        current_user: UserVO,
    ) -> L0AssemblyCostBatchResultVO:
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        bom_version = dto.bom_version.strip()
        count = self.cost_repo.reverse_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            reverse_audited_by=display_name(current_user),
            reverse_audited_at=now(),
            reverse_audit_remark=dto.reverse_audit_remark,
        )
        db.commit()
        return L0AssemblyCostBatchResultVO(
            affected_count=count,
            skipped_count=0,
            message=f"已反审核 {count} 条",
        )
