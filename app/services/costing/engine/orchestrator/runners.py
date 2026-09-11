"""引擎子计算：同进程调用各切片 Orchestrator，不嵌套 AsyncTask。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.common.types.repository_types import StepMetricsJson
from app.schemas.dto.assembly_cost_dto import AssemblyCostCalcDTO
from app.schemas.dto.bom_welding_fee_dto import BomWeldingFeeCalcDTO
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownGenerateDTO,
)
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeCalcDTO
from app.schemas.vo.costing_engine_vo import CostingEngineAnnualItemVO
from app.schemas.vo.user_vo import UserVO
from app.services.costing.engine.scope_discovery import DiscoveryResult, L0Scope
from app.services.costing.steel_price.calc.models import SteelPriceCalcRequest

if TYPE_CHECKING:
    from app.services.costing.engine.orchestrator.run_orchestrator import RunOrchestrator

logger = logging.getLogger("service.costing.engine.orchestrator")


def _calc_step_message(label: str, status: str) -> str:
    if status == "partial":
        return f"{label}部分成功，请到对应计算历史查看缺项"
    if status == "failed":
        return f"{label}失败"
    return f"{label}已完成"


def find_l0(discovery: DiscoveryResult, vehicle_model: str, bom_version: str) -> L0Scope | None:
    for scope in discovery.l0_scopes:
        if scope.vehicle_model == vehicle_model and scope.bom_version == bom_version:
            return scope
    return None


def run_annual_item(
    orch: RunOrchestrator,
    db: Session,
    *,
    discovery: DiscoveryResult,
    item: CostingEngineAnnualItemVO,
    current_user: UserVO,
) -> tuple[bool, str, StepMetricsJson | None]:
    try:
        if item.code == "annual_process_fee":
            process_fee_dto = StampingProcessFeeCalcDTO(
                year=discovery.year,
                location=discovery.location,
                vehicle_model=item.scope_key,
            )
            process_fee_result = orch.process_fee_orch.calculate(
                db, process_fee_dto, current_user=current_user
            )
            return (
                True,
                f"加工费补算完成 status={process_fee_result.status}",
                {"status": process_fee_result.status},
            )

        if item.code == "annual_welding_breakdown":
            vehicle_model, bom_version = item.scope_key.split("|", 1)
            scope = find_l0(discovery, vehicle_model, bom_version)
            breakdown_dto = BomWeldingProcessBreakdownGenerateDTO(
                location=scope.location if scope else discovery.location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
            )
            orch.breakdown_svc.generate(db, breakdown_dto, current_user=current_user)
            return (
                True,
                "焊接工艺拆解补算完成",
                {"result": True},
            )

        if item.code == "annual_welding_fee":
            vehicle_model, bom_version = item.scope_key.split("|", 1)
            scope = find_l0(discovery, vehicle_model, bom_version)
            weld_dto = BomWeldingFeeCalcDTO(
                year=discovery.year,
                location=scope.location if scope else discovery.location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
            )
            weld_result = orch.l0_welding_orch.calculate(db, weld_dto, current_user=current_user)
            return (
                True,
                f"焊接费补算完成 status={weld_result.status}",
                {"status": weld_result.status},
            )

        return False, f"未知年度补算 code={item.code}", None
    except Exception as exc:
        logger.exception("年度补算失败: %s %s", item.code, item.scope_key)
        db.rollback()
        return False, str(exc), None


def run_steel(
    orch: RunOrchestrator,
    db: Session,
    *,
    discovery: DiscoveryResult,
    current_user: UserVO,
) -> tuple[bool, str, StepMetricsJson | None]:
    try:
        request = SteelPriceCalcRequest(
            year=discovery.year,
            month=discovery.month,
            location=discovery.location,
        )
        result = orch.steel_orch.calculate(db, request, current_user=current_user)
        ok = result.status in ("success", "partial", "succeeded")
        if result.status == "failed":
            ok = False
        return (
            ok,
            _calc_step_message("钢材联动", result.status),
            {
                "status": result.status,
                "created_count": getattr(result, "created_count", None),
                "updated_count": getattr(result, "updated_count", None),
            },
        )
    except Exception as exc:
        logger.exception("钢材联动失败")
        db.rollback()
        return False, str(exc), None


def run_part_cost(
    orch: RunOrchestrator,
    db: Session,
    *,
    discovery: DiscoveryResult,
    vehicle_model: str,
    current_user: UserVO,
) -> tuple[bool, str, StepMetricsJson | None]:
    try:
        dto = StampingPartCostCalcDTO(
            year=discovery.year,
            month=discovery.month,
            location=discovery.location,
            vehicle_model=vehicle_model,
        )
        result = orch.part_cost_orch.calculate(db, dto, current_user=current_user)
        status = getattr(result, "status", "success")
        ok = status != "failed"
        return ok, _calc_step_message("零件核价", status), {"status": status}
    except Exception as exc:
        logger.exception("零件价失败: %s", vehicle_model)
        db.rollback()
        return False, str(exc), None


def run_assembly(
    orch: RunOrchestrator,
    db: Session,
    *,
    discovery: DiscoveryResult,
    scope: L0Scope,
    current_user: UserVO,
) -> tuple[bool, str, StepMetricsJson | None]:
    try:
        dto = AssemblyCostCalcDTO(
            year=discovery.year,
            month=discovery.month,
            location=scope.location,
            vehicle_model=scope.vehicle_model,
            bom_version=scope.bom_version,
        )
        result = orch.assembly_orch.calculate(db, dto, current_user=current_user)
        status = getattr(result, "status", "success")
        ok = status != "failed"
        return ok, _calc_step_message("总成核价", status), {"status": status}
    except Exception as exc:
        logger.exception("总成核价失败: %s/%s", scope.vehicle_model, scope.bom_version)
        db.rollback()
        return False, str(exc), None
