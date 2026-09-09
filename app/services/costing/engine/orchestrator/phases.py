"""核价引擎阶段循环：年度补算 / 钢材 / 零件价 / 总成。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.common.types.repository_types import EngineStepSummaryJson
from app.schemas.vo.costing_engine_vo import CostingEngineAnnualItemVO
from app.schemas.vo.user_vo import UserVO
from app.services.costing.engine.orchestrator.persist import add_step, finish_step
from app.services.costing.engine.orchestrator.runners import (
    run_annual_item,
    run_assembly,
    run_part_cost,
    run_steel,
)
from app.services.costing.engine.orchestrator.summary import resolve_run_status, step_summary
from app.services.costing.engine.progress import ProgressNotifier
from app.services.costing.engine.scope_discovery import DiscoveryResult

if TYPE_CHECKING:
    from app.services.costing.engine.orchestrator.run_orchestrator import RunOrchestrator


@dataclass(slots=True)
class PhaseCarry:
    failed_vehicles: set[str] = field(default_factory=set)
    failed_l0: set[str] = field(default_factory=set)
    step_summaries: list[EngineStepSummaryJson] = field(default_factory=list)
    run_status: str = "succeeded"
    halted_after_steel: bool = False


def execute_all_phases(
    orch: RunOrchestrator,
    db: Session,
    *,
    run_id: int,
    discovery: DiscoveryResult,
    annual_items: list[CostingEngineAnnualItemVO],
    current_user: UserVO,
    progress: ProgressNotifier,
) -> PhaseCarry:
    carry = PhaseCarry()
    execute_annual(
        orch,
        db,
        run_id=run_id,
        discovery=discovery,
        annual_items=annual_items,
        current_user=current_user,
        progress=progress,
        carry=carry,
    )
    steel_ok = execute_steel(
        orch,
        db,
        run_id=run_id,
        discovery=discovery,
        current_user=current_user,
        progress=progress,
        carry=carry,
    )
    if not steel_ok:
        carry.run_status = "failed"
        carry.halted_after_steel = True
        return carry
    execute_part_cost(
        orch,
        db,
        run_id=run_id,
        discovery=discovery,
        current_user=current_user,
        progress=progress,
        carry=carry,
    )
    execute_assembly(
        orch,
        db,
        run_id=run_id,
        discovery=discovery,
        current_user=current_user,
        progress=progress,
        carry=carry,
    )
    carry.run_status = resolve_run_status(carry.step_summaries)
    return carry


def execute_annual(
    orch: RunOrchestrator,
    db: Session,
    *,
    run_id: int,
    discovery: DiscoveryResult,
    annual_items: list[CostingEngineAnnualItemVO],
    current_user: UserVO,
    progress: ProgressNotifier,
    carry: PhaseCarry,
) -> None:
    annual_to_run = [i for i in annual_items if i.will_auto_calc]
    annual_total = max(len(annual_to_run), 1)
    annual_done = 0

    for item in annual_items:
        if not item.will_auto_calc:
            step = add_step(
                orch.run_repo,
                db,
                run_id,
                stage=item.code,
                scope_key=item.scope_key,
                status="skipped",
                message="已有结果，跳过补算",
            )
            carry.step_summaries.append(
                step_summary(step.stage, step.scope_key, "skipped", step.message)
            )
            continue

        if item.code == "annual_welding_fee" and item.scope_key in carry.failed_l0:
            step = finish_step(
                orch.run_repo,
                db,
                run_id=run_id,
                stage=item.code,
                scope_key=item.scope_key,
                status="skipped",
                message="焊接工艺拆解补算失败，跳过焊接费",
                metrics=None,
            )
            carry.step_summaries.append(
                step_summary(item.code, item.scope_key, "skipped", step.message)
            )
            annual_done += 1
            continue

        progress.report_stage(
            "annual",
            annual_done,
            annual_total,
            f"年度补算 · {item.code} · {item.scope_key}",
        )
        ok, message, metrics = run_annual_item(
            orch, db, discovery=discovery, item=item, current_user=current_user
        )
        status = "succeeded" if ok else "failed"
        if not ok and item.code == "annual_process_fee":
            carry.failed_vehicles.add(item.scope_key)
        if not ok and item.code == "annual_welding_breakdown":
            carry.failed_l0.add(item.scope_key)
        if not ok and item.code == "annual_welding_fee":
            carry.failed_l0.add(item.scope_key)
        step = finish_step(
            orch.run_repo,
            db,
            run_id=run_id,
            stage=item.code,
            scope_key=item.scope_key,
            status=status,
            message=message,
            metrics=metrics,
        )
        carry.step_summaries.append(step_summary(step.stage, step.scope_key, status, message))
        annual_done += 1
        progress.report_stage(
            "annual",
            annual_done,
            annual_total,
            f"年度补算 {annual_done}/{len(annual_to_run)}",
        )


def execute_steel(
    orch: RunOrchestrator,
    db: Session,
    *,
    run_id: int,
    discovery: DiscoveryResult,
    current_user: UserVO,
    progress: ProgressNotifier,
    carry: PhaseCarry,
) -> bool:
    progress.report_stage("steel", 0, 1, "钢材联动价计算…")
    steel_ok, steel_msg, steel_metrics = run_steel(
        orch, db, discovery=discovery, current_user=current_user
    )
    steel_status = "succeeded" if steel_ok else "failed"
    finish_step(
        orch.run_repo,
        db,
        run_id=run_id,
        stage="steel",
        scope_key=discovery.location,
        status=steel_status,
        message=steel_msg,
        metrics=steel_metrics,
    )
    carry.step_summaries.append(step_summary("steel", discovery.location, steel_status, steel_msg))
    progress.report_stage("steel", 1, 1, steel_msg or "钢材联动完成")
    return steel_ok


def execute_part_cost(
    orch: RunOrchestrator,
    db: Session,
    *,
    run_id: int,
    discovery: DiscoveryResult,
    current_user: UserVO,
    progress: ProgressNotifier,
    carry: PhaseCarry,
) -> None:
    vehicles = discovery.stamping_vehicle_models
    part_total = max(len(vehicles), 1)
    for idx, vehicle_model in enumerate(vehicles):
        progress.report_stage(
            "part_cost",
            idx,
            part_total,
            f"零件价 {idx + 1}/{len(vehicles)} · {vehicle_model}",
        )
        if vehicle_model in carry.failed_vehicles:
            step = finish_step(
                orch.run_repo,
                db,
                run_id=run_id,
                stage="part_cost",
                scope_key=vehicle_model,
                status="skipped",
                message="加工费补算失败，跳过零件价",
                metrics=None,
            )
            carry.step_summaries.append(
                step_summary("part_cost", vehicle_model, "skipped", step.message)
            )
            continue

        ok, message, metrics = run_part_cost(
            orch,
            db,
            discovery=discovery,
            vehicle_model=vehicle_model,
            current_user=current_user,
        )
        status = "succeeded" if ok else "failed"
        if not ok:
            carry.failed_vehicles.add(vehicle_model)
        finish_step(
            orch.run_repo,
            db,
            run_id=run_id,
            stage="part_cost",
            scope_key=vehicle_model,
            status=status,
            message=message,
            metrics=metrics,
        )
        carry.step_summaries.append(step_summary("part_cost", vehicle_model, status, message))
        progress.report_stage(
            "part_cost",
            idx + 1,
            part_total,
            f"零件价 {idx + 1}/{len(vehicles)} · {vehicle_model}",
        )


def execute_assembly(
    orch: RunOrchestrator,
    db: Session,
    *,
    run_id: int,
    discovery: DiscoveryResult,
    current_user: UserVO,
    progress: ProgressNotifier,
    carry: PhaseCarry,
) -> None:
    scopes = discovery.l0_scopes
    stamping_models = set(discovery.stamping_vehicle_models)
    total = max(len(scopes), 1)
    for idx, scope in enumerate(scopes):
        scope_key = f"{scope.vehicle_model}|{scope.bom_version}"
        progress.report_stage(
            "assembly",
            idx,
            total,
            f"总成核价 {idx + 1}/{len(scopes)} · {scope.vehicle_model} / {scope.bom_version}",
        )
        skip_reason = None
        if scope.vehicle_model in stamping_models and scope.vehicle_model in carry.failed_vehicles:
            skip_reason = "该项目加工费或零件价未完成，跳过总成核价"
        elif scope_key in carry.failed_l0:
            skip_reason = "年度焊接拆解/焊接费补算失败，跳过总成核价"
        if skip_reason:
            step = finish_step(
                orch.run_repo,
                db,
                run_id=run_id,
                stage="assembly",
                scope_key=scope_key,
                status="skipped",
                message=skip_reason,
                metrics=None,
            )
            carry.step_summaries.append(
                step_summary("assembly", scope_key, "skipped", step.message)
            )
            continue

        ok, message, metrics = run_assembly(
            orch, db, discovery=discovery, scope=scope, current_user=current_user
        )
        status = "succeeded" if ok else "failed"
        finish_step(
            orch.run_repo,
            db,
            run_id=run_id,
            stage="assembly",
            scope_key=scope_key,
            status=status,
            message=message,
            metrics=metrics,
        )
        carry.step_summaries.append(step_summary("assembly", scope_key, status, message))
        progress.report_stage(
            "assembly",
            idx + 1,
            total,
            f"总成核价 {idx + 1}/{len(scopes)} · {scope.vehicle_model} / {scope.bom_version}",
        )
