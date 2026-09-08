"""引擎 Run / step 落库（commit 只在本文件）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.common.types.repository_types import StepMetricsJson, SummaryJson
from app.models.costing.costing_engine_run_step import CostingEngineRunStep
from app.repositories.costing.engine.costing_engine_run_repository import (
    CostingEngineRunRepository,
)
from app.services.costing.engine.orchestrator.errors import RunDeletedError
from app.services.costing.engine.orchestrator.prep import ensure_run
from app.services.costing.engine.orchestrator.summary import build_summary
from app.services.costing.engine.progress import ProgressNotifier
from app.services.costing.engine.scope_discovery import DiscoveryResult

if TYPE_CHECKING:
    from app.services.costing.engine.orchestrator.phases import PhaseCarry


def add_step(
    run_repo: CostingEngineRunRepository,
    db: Session,
    run_id: int,
    *,
    stage: str,
    scope_key: str,
    status: str,
    message: str | None,
) -> CostingEngineRunStep:
    ensure_run(run_repo, db, run_id)
    step = run_repo.create_step(
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


def finish_step(
    run_repo: CostingEngineRunRepository,
    db: Session,
    *,
    run_id: int,
    stage: str,
    scope_key: str,
    status: str,
    message: str | None,
    metrics: StepMetricsJson | None,
) -> CostingEngineRunStep:
    ensure_run(run_repo, db, run_id)
    step = run_repo.create_step(
        db,
        run_id=run_id,
        stage=stage,
        scope_key=scope_key,
        status="running",
        message=None,
    )
    started = now()
    run_repo.update_step_fields(
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


def finalize_run(
    run_repo: CostingEngineRunRepository,
    db: Session,
    run_id: int,
    *,
    status: str,
    summary: SummaryJson,
) -> None:
    try:
        run = ensure_run(run_repo, db, run_id)
    except RunDeletedError:
        return
    run_repo.update_run_fields(
        db,
        run,
        status=status,
        summary_json=summary,
        finished_at=now(),
    )
    db.commit()


def finalize_execute(
    run_repo: CostingEngineRunRepository,
    db: Session,
    run_id: int,
    discovery: DiscoveryResult,
    carry: PhaseCarry,
    progress: ProgressNotifier,
) -> SummaryJson:
    summary = build_summary(discovery, carry.step_summaries, run_status=carry.run_status)
    if not carry.halted_after_steel:
        progress.report_stage("summary", 1, 1, f"完成 · {carry.run_status}")
    finalize_run(run_repo, db, run_id, status=carry.run_status, summary=summary)
    return summary
