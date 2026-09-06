"""核价引擎 — 年度补算计划。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.schemas.vo.costing_engine_vo import CostingEngineAnnualItemVO
from app.services.costing.engine.scope_discovery import DiscoveryResult
from app.services.costing.stamping_part_cost.helpers import location_candidates

_ANY_STATUS = [AUDIT_PENDING, AUDIT_APPROVED, AUDIT_REJECTED]


class AnnualCalcPlanner:
    """§5.2：缺失年度结果 → will_auto_calc。"""

    def __init__(self) -> None:
        self.process_fee_repo = StampingProcessFeeRepository()
        self.breakdown_repo = BomWeldingProcessBreakdownRepository()
        self.l0_welding_fee_repo = BomWeldingFeeRepository()

    def plan(self, db: Session, discovery: DiscoveryResult) -> list[CostingEngineAnnualItemVO]:
        items: list[CostingEngineAnnualItemVO] = []
        aliases = discovery.location_aliases or location_candidates(discovery.location)

        for vehicle_model in discovery.vehicle_models:
            exists = self._process_fee_exists(
                db,
                year=discovery.year,
                aliases=aliases,
                vehicle_model=vehicle_model,
            )
            items.append(
                CostingEngineAnnualItemVO(
                    code="annual_process_fee",
                    scope_key=vehicle_model,
                    exists=exists,
                    will_auto_calc=not exists,
                )
            )

        for scope in discovery.l0_scopes:
            scope_key = f"{scope.vehicle_model}|{scope.bom_version}"
            breakdown_exists = (
                self.breakdown_repo.count_by_scope(
                    db,
                    location=scope.location,
                    vehicle_model=scope.vehicle_model,
                    bom_version=scope.bom_version,
                )
                > 0
            )
            items.append(
                CostingEngineAnnualItemVO(
                    code="annual_welding_breakdown",
                    scope_key=scope_key,
                    exists=breakdown_exists,
                    will_auto_calc=not breakdown_exists,
                )
            )

            welding_fee_exists = self._l0_welding_fee_exists(
                db,
                year=discovery.year,
                location=scope.location,
                vehicle_model=scope.vehicle_model,
                bom_version=scope.bom_version,
            )
            items.append(
                CostingEngineAnnualItemVO(
                    code="annual_welding_fee",
                    scope_key=scope_key,
                    exists=welding_fee_exists,
                    will_auto_calc=not welding_fee_exists,
                )
            )

        return items

    def _process_fee_exists(
        self,
        db: Session,
        *,
        year: int,
        aliases: list[str],
        vehicle_model: str,
    ) -> bool:
        for alias in aliases:
            if (
                self.process_fee_repo.count_by_scope_and_statuses(
                    db,
                    year=year,
                    location=alias,
                    vehicle_model=vehicle_model,
                    statuses=_ANY_STATUS,
                )
                > 0
            ):
                return True
        return False

    def _l0_welding_fee_exists(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> bool:
        return (
            self.l0_welding_fee_repo.count_by_scope_and_statuses(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                statuses=_ANY_STATUS,
                level=None,
            )
            > 0
        )
