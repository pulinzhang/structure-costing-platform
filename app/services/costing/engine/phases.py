"""核价引擎阶段循环：年度补算 / 钢材 / 零件价 / L0。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.schemas.vo.costing_engine_vo import CostingEngineAnnualItemVO
from app.schemas.vo.user_vo import UserVO
from app.services.costing.engine.progress import ProgressNotifier
from app.services.costing.engine.scope_discovery import DiscoveryResult

if TYPE_CHECKING:
    from app.services.costing.engine.run_orchestrator import RunOrchestrator


@dataclass(slots=True)
class PhaseCarry:
    failed_suppliers: set[str] = field(default_factory=set)
    failed_l0: set[str] = field(default_factory=set)
    step_summaries: list[dict[str, Any]] = field(default_factory=list)


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
            step = orch._add_step(
                db,
                run_id,
                stage=item.code,
                scope_key=item.scope_key,
                status="skipped",
                message="已有结果，跳过补算",
            )
            carry.step_summaries.append(
                orch._step_summary(step.stage, step.scope_key, "skipped", step.message)
            )
            continue

        if item.code == "annual_l0_welding_fee" and item.scope_key in carry.failed_l0:
            step = orch._finish_step(
                db,
                run_id=run_id,
                stage=item.code,
                scope_key=item.scope_key,
                status="skipped",
                message="焊接工艺拆解补算失败，跳过 L0 焊接费",
                metrics=None,
            )
            carry.step_summaries.append(
                orch._step_summary(item.code, item.scope_key, "skipped", step.message)
            )
            annual_done += 1
            continue

        progress.report_stage(
            "annual",
            annual_done,
            annual_total,
            f"年度补算 · {item.code} · {item.scope_key}",
        )
        ok, message, metrics = orch._run_annual_item(
            db, discovery=discovery, item=item, current_user=current_user
        )
        status = "succeeded" if ok else "failed"
        if not ok and item.code == "annual_process_fee":
            carry.failed_suppliers.add(item.scope_key)
        if not ok and item.code == "annual_welding_breakdown":
            carry.failed_l0.add(item.scope_key)
        if not ok and item.code == "annual_l0_welding_fee":
            carry.failed_l0.add(item.scope_key)
        step = orch._finish_step(
            db,
            run_id=run_id,
            stage=item.code,
            scope_key=item.scope_key,
            status=status,
            message=message,
            metrics=metrics,
        )
        carry.step_summaries.append(orch._step_summary(step.stage, step.scope_key, status, message))
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
    steel_ok, steel_msg, steel_metrics = orch._run_steel(
        db, discovery=discovery, current_user=current_user
    )
    steel_status = "succeeded" if steel_ok else "failed"
    orch._finish_step(
        db,
        run_id=run_id,
        stage="steel",
        scope_key=discovery.location,
        status=steel_status,
        message=steel_msg,
        metrics=steel_metrics,
    )
    carry.step_summaries.append(
        orch._step_summary("steel", discovery.location, steel_status, steel_msg)
    )
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
    suppliers = discovery.stamping_suppliers
    part_total = max(len(suppliers), 1)
    for idx, supplier in enumerate(suppliers):
        progress.report_stage(
            "part_cost",
            idx,
            part_total,
            f"零件价 {idx + 1}/{len(suppliers)} · {supplier}",
        )
        if supplier in carry.failed_suppliers:
            step = orch._finish_step(
                db,
                run_id=run_id,
                stage="part_cost",
                scope_key=supplier,
                status="skipped",
                message="加工费补算失败，跳过零件价",
                metrics=None,
            )
            carry.step_summaries.append(
                orch._step_summary("part_cost", supplier, "skipped", step.message)
            )
            continue

        ok, message, metrics = orch._run_part_cost(
            db,
            discovery=discovery,
            stamping_supplier=supplier,
            current_user=current_user,
        )
        status = "succeeded" if ok else "failed"
        orch._finish_step(
            db,
            run_id=run_id,
            stage="part_cost",
            scope_key=supplier,
            status=status,
            message=message,
            metrics=metrics,
        )
        carry.step_summaries.append(orch._step_summary("part_cost", supplier, status, message))
        progress.report_stage(
            "part_cost",
            idx + 1,
            part_total,
            f"零件价 {idx + 1}/{len(suppliers)} · {supplier}",
        )


def execute_l0(
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
    l0_total = max(len(scopes), 1)
    for idx, scope in enumerate(scopes):
        scope_key = f"{scope.vehicle_model}|{scope.bom_version}"
        progress.report_stage(
            "l0",
            idx,
            l0_total,
            f"L0 核价 {idx + 1}/{len(scopes)} · {scope.vehicle_model} / {scope.bom_version}",
        )
        if scope_key in carry.failed_l0:
            step = orch._finish_step(
                db,
                run_id=run_id,
                stage="l0",
                scope_key=scope_key,
                status="skipped",
                message="年度焊接拆解/焊接费补算失败，跳过成品核价",
                metrics=None,
            )
            carry.step_summaries.append(
                orch._step_summary("l0", scope_key, "skipped", step.message)
            )
            continue

        ok, message, metrics = orch._run_l0(
            db, discovery=discovery, scope=scope, current_user=current_user
        )
        status = "succeeded" if ok else "failed"
        orch._finish_step(
            db,
            run_id=run_id,
            stage="l0",
            scope_key=scope_key,
            status=status,
            message=message,
            metrics=metrics,
        )
        carry.step_summaries.append(orch._step_summary("l0", scope_key, status, message))
        progress.report_stage(
            "l0",
            idx + 1,
            l0_total,
            f"L0 核价 {idx + 1}/{len(scopes)} · {scope.vehicle_model} / {scope.bom_version}",
        )
