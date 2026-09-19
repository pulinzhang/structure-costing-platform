"""核价引擎 — 年度补算计划。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.costing_engine_vo import CostingEngineAnnualItemVO
from app.services.bom.procurement_object.coverage import (
    evaluate_procurement_object_coverage,
)
from app.services.costing.assembly_cost.calc.orchestrator.ready import (
    evaluate_welding_coverage,
)
from app.services.costing.engine.scope_discovery import DiscoveryResult
from app.services.stamping.die_fee.calc.orchestrator.ready import (
    evaluate_die_fee_coverage,
)
from app.services.stamping.process_fee.calc.orchestrator.ready import (
    evaluate_process_fee_coverage,
)


class AnnualCalcPlanner:
    """§5.2：有工艺才判冲压加工费；有布点才判模具费；有 BOM 才判采购对象 / 焊接。"""

    def plan(self, db: Session, discovery: DiscoveryResult) -> list[CostingEngineAnnualItemVO]:
        items: list[CostingEngineAnnualItemVO] = []

        for vehicle_model in discovery.stamping_vehicle_models:
            process_fee = evaluate_process_fee_coverage(
                db,
                year=discovery.year,
                aliases=discovery.location_aliases,
                vehicle_model=vehicle_model,
            )
            items.append(
                CostingEngineAnnualItemVO(
                    code="annual_process_fee",
                    scope_key=vehicle_model,
                    exists=process_fee.complete,
                    will_auto_calc=not process_fee.complete,
                )
            )

        for vehicle_model in discovery.vehicle_models:
            die_fee = evaluate_die_fee_coverage(
                db,
                year=discovery.year,
                aliases=discovery.location_aliases,
                vehicle_model=vehicle_model,
            )
            if not die_fee.has_dies:
                continue
            items.append(
                CostingEngineAnnualItemVO(
                    code="annual_die_fee",
                    scope_key=vehicle_model,
                    exists=die_fee.complete,
                    will_auto_calc=not die_fee.complete,
                )
            )

        for scope in discovery.l0_scopes:
            scope_key = f"{scope.vehicle_model}|{scope.bom_version}"
            procurement = evaluate_procurement_object_coverage(
                db,
                location=scope.location,
                vehicle_model=scope.vehicle_model,
                bom_version=scope.bom_version,
            )
            items.append(
                CostingEngineAnnualItemVO(
                    code="annual_procurement_object",
                    scope_key=scope_key,
                    exists=procurement.complete,
                    will_auto_calc=not procurement.complete,
                )
            )
            welding = evaluate_welding_coverage(
                db,
                year=discovery.year,
                location=scope.location,
                vehicle_model=scope.vehicle_model,
                bom_version=scope.bom_version,
            )
            items.append(
                CostingEngineAnnualItemVO(
                    code="annual_welding_breakdown",
                    scope_key=scope_key,
                    exists=welding.breakdown_complete,
                    will_auto_calc=not welding.breakdown_complete,
                )
            )
            items.append(
                CostingEngineAnnualItemVO(
                    code="annual_welding_fee",
                    scope_key=scope_key,
                    exists=welding.complete,
                    will_auto_calc=not welding.complete,
                )
            )

        return items
