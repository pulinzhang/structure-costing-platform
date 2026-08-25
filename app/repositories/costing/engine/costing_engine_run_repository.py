"""核价引擎 Run / Step 数据访问。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.costing.costing_engine_run import CostingEngineRun
from app.models.costing.costing_engine_run_step import CostingEngineRunStep


class CostingEngineRunRepository:
    """引擎编排账本 Repository。"""

    def get_by_id(self, db: Session, run_id: int) -> CostingEngineRun | None:
        return (
            db.query(CostingEngineRun)
            .options(joinedload(CostingEngineRun.steps))
            .filter(CostingEngineRun.id == run_id)
            .first()
        )

    def get_by_task_id(self, db: Session, task_id: str) -> CostingEngineRun | None:
        return (
            db.query(CostingEngineRun)
            .options(joinedload(CostingEngineRun.steps))
            .filter(CostingEngineRun.task_id == task_id)
            .first()
        )

    def get_running_by_key(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineRun | None:
        return (
            db.query(CostingEngineRun)
            .filter(
                CostingEngineRun.location == location,
                CostingEngineRun.year == year,
                CostingEngineRun.month == month,
                CostingEngineRun.status == "running",
            )
            .order_by(CostingEngineRun.id.desc())
            .first()
        )

    def create(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        month: int,
        status: str,
        task_id: str | None,
        gate_json: dict[str, Any] | None,
        plan_json: dict[str, Any] | None,
        created_by: str | None,
        updated_by: str | None,
        started_at: datetime | None,
    ) -> CostingEngineRun:
        row = CostingEngineRun(
            location=location,
            year=year,
            month=month,
            status=status,
            task_id=task_id,
            gate_json=gate_json,
            plan_json=plan_json,
            created_by=created_by,
            updated_by=updated_by,
            started_at=started_at,
        )
        db.add(row)
        db.flush()
        return row

    def create_step(
        self,
        db: Session,
        *,
        run_id: int,
        stage: str,
        scope_key: str,
        status: str = "pending",
        message: str | None = None,
    ) -> CostingEngineRunStep:
        step = CostingEngineRunStep(
            run_id=run_id,
            stage=stage,
            scope_key=scope_key,
            status=status,
            message=message,
        )
        db.add(step)
        db.flush()
        return step

    def get_step(self, db: Session, step_id: int) -> CostingEngineRunStep | None:
        return db.query(CostingEngineRunStep).filter(CostingEngineRunStep.id == step_id).first()

    def update_run_fields(
        self,
        db: Session,
        run: CostingEngineRun,
        *,
        status: str | None = None,
        summary_json: dict[str, Any] | None = None,
        finished_at: datetime | None = None,
        updated_by: str | None = None,
    ) -> CostingEngineRun:
        if status is not None:
            run.status = status
        if summary_json is not None:
            run.summary_json = summary_json
        if finished_at is not None:
            run.finished_at = finished_at
        if updated_by is not None:
            run.updated_by = updated_by
        db.flush()
        return run

    def update_step_fields(
        self,
        db: Session,
        step: CostingEngineRunStep,
        *,
        status: str | None = None,
        message: str | None = None,
        metrics_json: dict[str, Any] | None = None,
        child_log_id: int | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> CostingEngineRunStep:
        if status is not None:
            step.status = status
        if message is not None:
            step.message = message
        if metrics_json is not None:
            step.metrics_json = metrics_json
        if child_log_id is not None:
            step.child_log_id = child_log_id
        if started_at is not None:
            step.started_at = started_at
        if finished_at is not None:
            step.finished_at = finished_at
        db.flush()
        return step

    def paginate(
        self,
        db: Session,
        *,
        location: str | None = None,
        year: int | None = None,
        month: int | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[CostingEngineRun], int]:
        q = db.query(CostingEngineRun)
        if location:
            q = q.filter(CostingEngineRun.location == location)
        if year is not None:
            q = q.filter(CostingEngineRun.year == year)
        if month is not None:
            q = q.filter(CostingEngineRun.month == month)
        if status:
            q = q.filter(CostingEngineRun.status == status)
        total = q.count()
        rows = q.order_by(CostingEngineRun.id.desc()).offset(skip).limit(limit).all()
        return rows, total

    def delete(self, db: Session, run_id: int) -> bool:
        row = db.query(CostingEngineRun).filter(CostingEngineRun.id == run_id).first()
        if row is None:
            return False
        db.delete(row)
        db.flush()
        return True
