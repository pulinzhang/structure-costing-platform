"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

核价引擎 — DAG 串行编排（同进程调用子计算）。
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.models.costing.costing_engine_run import CostingEngineRun
from app.repositories.costing.engine.costing_engine_run_repository import (
    CostingEngineRunRepository,
)
from app.schemas.dto.bom_l0_welding_fee_dto import BomL0WeldingFeeCalcDTO
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownGenerateDTO,
)
from app.schemas.dto.l0_assembly_cost_dto import L0AssemblyCostCalcDTO
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeCalcDTO
from app.schemas.vo.costing_engine_vo import CostingEngineAnnualItemVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.l0_welding_fee.calc.orchestrator import BomL0WeldingFeeCalcOrchestrator
from app.services.bom.welding_process_breakdown.generate_service import (
    BomWeldingProcessBreakdownGenerateService,
)
from app.services.costing.engine.phases import (
    PhaseCarry,
    execute_annual,
    execute_l0,
    execute_part_cost,
    execute_steel,
)
from app.services.costing.engine.progress import ProgressFn, ProgressNotifier
from app.services.costing.engine.scope_discovery import DiscoveryResult, L0Scope
from app.services.costing.l0_assembly_cost.calc.orchestrator import (
    L0AssemblyCostCalcOrchestrator,
)
from app.services.costing.steel_price.calc.models import SteelPriceCalcRequest
from app.services.costing.steel_price.calc.orchestrator import SteelPriceCalcOrchestrator
from app.services.costing.stamping_part_cost.calc.orchestrator import (
    StampingPartCostCalcOrchestrator,
)
from app.services.stamping.process_fee.calc.orchestrator import (
    StampingProcessFeeCalcOrchestrator,
)

logger = logging.getLogger("service.costing.engine.orchestrator")


class RunDeletedError(Exception):
    """Run 已被用户删除，Worker 应安静退出。"""


class RunOrchestrator:
    """Phase3 年度补算 + Phase4 月度主链。"""

    def __init__(self) -> None:
        self.run_repo = CostingEngineRunRepository()
        self.process_fee_orch = StampingProcessFeeCalcOrchestrator()
        self.breakdown_svc = BomWeldingProcessBreakdownGenerateService()
        self.l0_welding_orch = BomL0WeldingFeeCalcOrchestrator()
        self.steel_orch = SteelPriceCalcOrchestrator()
        self.part_cost_orch = StampingPartCostCalcOrchestrator()
        self.l0_orch = L0AssemblyCostCalcOrchestrator()

    def execute(
        self,
        db: Session,
        *,
        run_id: int,
        discovery: DiscoveryResult,
        annual_items: list[CostingEngineAnnualItemVO],
        current_user: UserVO,
        progress_callback: ProgressFn | None = None,
    ) -> dict[str, Any]:
        progress = ProgressNotifier(progress_callback)
        self._ensure_run(db, run_id)
        progress.report_stage("gate_plan", 1, 1, "门禁已通过，开始执行")

        carry = PhaseCarry()
        execute_annual(
            self,
            db,
            run_id=run_id,
            discovery=discovery,
            annual_items=annual_items,
            current_user=current_user,
            progress=progress,
            carry=carry,
        )
        steel_ok = execute_steel(
            self,
            db,
            run_id=run_id,
            discovery=discovery,
            current_user=current_user,
            progress=progress,
            carry=carry,
        )
        if not steel_ok:
            summary = self._build_summary(discovery, carry.step_summaries, run_status="failed")
            self._finalize_run(db, run_id, status="failed", summary=summary)
            return summary

        execute_part_cost(
            self,
            db,
            run_id=run_id,
            discovery=discovery,
            current_user=current_user,
            progress=progress,
            carry=carry,
        )
        execute_l0(
            self,
            db,
            run_id=run_id,
            discovery=discovery,
            current_user=current_user,
            progress=progress,
            carry=carry,
        )

        run_status = self._resolve_run_status(carry.step_summaries)
        summary = self._build_summary(discovery, carry.step_summaries, run_status=run_status)
        progress.report_stage("summary", 1, 1, f"完成 · {run_status}")
        self._finalize_run(db, run_id, status=run_status, summary=summary)
        return summary

    # ----- annual / monthly runners -----

    def _run_annual_item(
        self,
        db: Session,
        *,
        discovery: DiscoveryResult,
        item: CostingEngineAnnualItemVO,
        current_user: UserVO,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        try:
            if item.code == "annual_process_fee":
                process_fee_dto = StampingProcessFeeCalcDTO(
                    year=discovery.year,
                    location=discovery.location,
                    stamping_supplier=item.scope_key,
                )
                process_fee_result = self.process_fee_orch.calculate(
                    db, process_fee_dto, current_user=current_user
                )
                return (
                    True,
                    f"加工费补算完成 status={process_fee_result.status}",
                    {"status": process_fee_result.status},
                )

            if item.code == "annual_welding_breakdown":
                vehicle_model, bom_version = item.scope_key.split("|", 1)
                scope = self._find_l0(discovery, vehicle_model, bom_version)
                breakdown_dto = BomWeldingProcessBreakdownGenerateDTO(
                    location=scope.location if scope else discovery.location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                )
                result_vo, error = self.breakdown_svc.generate(
                    db, breakdown_dto, current_user=current_user
                )
                if error:
                    return False, error, None
                return (
                    True,
                    "焊接工艺拆解补算完成",
                    {
                        "result": bool(result_vo),
                    },
                )

            if item.code == "annual_l0_welding_fee":
                vehicle_model, bom_version = item.scope_key.split("|", 1)
                scope = self._find_l0(discovery, vehicle_model, bom_version)
                l0_dto = BomL0WeldingFeeCalcDTO(
                    year=discovery.year,
                    location=scope.location if scope else discovery.location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                )
                l0_result = self.l0_welding_orch.calculate(db, l0_dto, current_user=current_user)
                return (
                    True,
                    f"L0 焊接费补算完成 status={l0_result.status}",
                    {"status": l0_result.status},
                )

            return False, f"未知年度补算 code={item.code}", None
        except Exception as exc:
            logger.exception("年度补算失败: %s %s", item.code, item.scope_key)
            db.rollback()
            return False, str(exc), None

    def _run_steel(
        self,
        db: Session,
        *,
        discovery: DiscoveryResult,
        current_user: UserVO,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        try:
            request = SteelPriceCalcRequest(
                year=discovery.year,
                month=discovery.month,
                location=discovery.location,
            )
            result = self.steel_orch.calculate(db, request, current_user=current_user)
            ok = result.status in ("success", "partial", "succeeded")
            # steel uses success/partial/failed
            if result.status == "failed":
                ok = False
            return (
                ok,
                f"钢材联动 status={result.status}",
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

    def _run_part_cost(
        self,
        db: Session,
        *,
        discovery: DiscoveryResult,
        stamping_supplier: str,
        current_user: UserVO,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        try:
            dto = StampingPartCostCalcDTO(
                year=discovery.year,
                month=discovery.month,
                location=discovery.location,
                stamping_supplier=stamping_supplier,
            )
            result = self.part_cost_orch.calculate(db, dto, current_user=current_user)
            status = getattr(result, "status", "success")
            ok = status != "failed"
            return ok, f"零件价 status={status}", {"status": status}
        except Exception as exc:
            logger.exception("零件价失败: %s", stamping_supplier)
            db.rollback()
            return False, str(exc), None

    def _run_l0(
        self,
        db: Session,
        *,
        discovery: DiscoveryResult,
        scope: L0Scope,
        current_user: UserVO,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        try:
            dto = L0AssemblyCostCalcDTO(
                year=discovery.year,
                month=discovery.month,
                location=scope.location,
                vehicle_model=scope.vehicle_model,
                bom_version=scope.bom_version,
            )
            result = self.l0_orch.calculate(db, dto, current_user=current_user)
            status = getattr(result, "status", "success")
            ok = status != "failed"
            return ok, f"L0 核价 status={status}", {"status": status}
        except Exception as exc:
            logger.exception("L0 核价失败: %s/%s", scope.vehicle_model, scope.bom_version)
            db.rollback()
            return False, str(exc), None

    # ----- persistence helpers -----

    def _ensure_run(self, db: Session, run_id: int) -> CostingEngineRun:
        run = self.run_repo.get_by_id(db, run_id)
        if run is None:
            raise RunDeletedError(f"run {run_id} deleted")
        return run

    def _add_step(
        self,
        db: Session,
        run_id: int,
        *,
        stage: str,
        scope_key: str,
        status: str,
        message: str | None,
    ) -> Any:
        self._ensure_run(db, run_id)
        step = self.run_repo.create_step(
            db,
            run_id=run_id,
            stage=stage,
            scope_key=scope_key,
            status=status,
            message=message,
        )
        step.finished_at = now()
        db.flush()
        db.commit()
        return step

    def _finish_step(
        self,
        db: Session,
        *,
        run_id: int,
        stage: str,
        scope_key: str,
        status: str,
        message: str | None,
        metrics: dict[str, Any] | None,
    ) -> Any:
        self._ensure_run(db, run_id)
        step = self.run_repo.create_step(
            db,
            run_id=run_id,
            stage=stage,
            scope_key=scope_key,
            status="running",
            message=None,
        )
        started = now()
        self.run_repo.update_step_fields(
            db,
            step,
            status=status,
            message=message,
            metrics_json=metrics,
            started_at=started,
            finished_at=now(),
        )
        db.commit()
        return step

    def _finalize_run(
        self,
        db: Session,
        run_id: int,
        *,
        status: str,
        summary: dict[str, Any],
    ) -> None:
        try:
            run = self._ensure_run(db, run_id)
        except RunDeletedError:
            return
        self.run_repo.update_run_fields(
            db,
            run,
            status=status,
            summary_json=summary,
            finished_at=now(),
        )
        db.commit()

    @staticmethod
    def _find_l0(
        discovery: DiscoveryResult, vehicle_model: str, bom_version: str
    ) -> L0Scope | None:
        for scope in discovery.l0_scopes:
            if scope.vehicle_model == vehicle_model and scope.bom_version == bom_version:
                return scope
        return None

    @staticmethod
    def _step_summary(
        stage: str, scope_key: str, status: str, message: str | None
    ) -> dict[str, Any]:
        return {
            "stage": stage,
            "scope_key": scope_key,
            "status": status,
            "message": message,
        }

    @staticmethod
    def _resolve_run_status(steps: list[dict[str, Any]]) -> str:
        statuses = [s["status"] for s in steps]
        has_success = any(s in ("succeeded", "skipped") for s in statuses)
        has_failed = any(s == "failed" for s in statuses)
        # skipped 因已有结果算成功路径；因上游失败的 skipped 仍算未全绿
        if has_failed and has_success:
            return "partial"
        if has_failed and not has_success:
            return "failed"
        return "succeeded"

    @staticmethod
    def _build_summary(
        discovery: DiscoveryResult,
        steps: list[dict[str, Any]],
        *,
        run_status: str,
    ) -> dict[str, Any]:
        counts = {"succeeded": 0, "failed": 0, "skipped": 0}
        for step in steps:
            key = step["status"]
            if key in counts:
                counts[key] += 1
        return {
            "status": run_status,
            "location": discovery.location,
            "year": discovery.year,
            "month": discovery.month,
            "steps": steps,
            "counts": counts,
        }
