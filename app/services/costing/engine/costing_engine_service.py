"""核价引擎 — 编排唯一入口。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import cast

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.duration import duration_seconds as calc_duration_seconds
from app.common.timezone import datetime_to_iso, now
from app.common.types.repository_types import (
    EngineWorkerResultJson,
    GateJson,
    PlanJson,
    SummaryJson,
)
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.costing.engine.costing_engine_run_repository import (
    CostingEngineRunRepository,
)
from app.schemas.common import DeletedCountVO
from app.schemas.dto.costing_engine_dto import CostingEngineRunCreateDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.costing_engine_vo import (
    CostingEngineGateItemVO,
    CostingEngineGatesVO,
    CostingEngineL0ScopeVO,
    CostingEnginePartCostScopeVO,
    CostingEnginePlanVO,
    CostingEngineReadyVO,
    CostingEngineRunListItemVO,
    CostingEngineRunVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    TASK_TYPE_COSTING_ENGINE_RUN,
    AsyncTaskService,
    WorkerTaskOutcome,
)
from app.services.async_task.worker_runner import ProgressCallback
from app.services.costing.engine.annual_calc_planner import AnnualCalcPlanner
from app.services.costing.engine.gate_checker import GateChecker
from app.services.costing.engine.orchestrator import RunOrchestrator
from app.services.costing.engine.orchestrator.errors import RunDeletedError
from app.services.costing.engine.scope_discovery import ScopeDiscovery
from app.services.masterdata.location.location_service import LocationService

logger = logging.getLogger("service.costing.engine")

# 仍展示「去处理」提示，但不计入 hard_stop / 不阻断 can_start
# 缺工艺/无 BOM / 该月无命中零件或树 只提示；无路径时仍靠 has_path 禁止启动
SOFT_UPLOAD_GATE_CODES = frozenset(
    {
        "packaging_transport",
        "stamping_process",
        "bom_snapshot",
        "vehicle_model",
        "vehicle_model_period",
    }
)


def _run_timing_payload(
    started_at: datetime | None,
    finished_at: datetime | None,
) -> EngineWorkerResultJson:
    """从 Run 起止时间拼 worker result 的耗时字段。"""
    payload: EngineWorkerResultJson = {}
    started_iso = datetime_to_iso(started_at)
    if started_iso is not None:
        payload["started_at"] = started_iso
    finished_iso = datetime_to_iso(finished_at)
    if finished_iso is not None:
        payload["finished_at"] = finished_iso
    seconds = calc_duration_seconds(started_at, finished_at)
    if seconds is not None:
        payload["duration_seconds"] = seconds
    return payload


class CostingEngineHardStopError(BusinessException):
    """硬门禁未通过；Router 可将 upload_or_config 放入 fail.data。"""

    def __init__(
        self,
        message: str,
        *,
        upload_or_config: list[CostingEngineGateItemVO],
    ):
        super().__init__(
            message=message,
            code=400,
            data={
                "hard_stop": True,
                "can_start": False,
                "upload_or_config": [
                    item.model_dump(exclude_none=True) for item in upload_or_config
                ],
            },
        )
        self.upload_or_config = upload_or_config


class CostingEngineService:
    """月度智能自动核价引擎。"""

    def __init__(self) -> None:
        self.discovery = ScopeDiscovery()
        self.gate_checker = GateChecker()
        self.annual_planner = AnnualCalcPlanner()
        self.run_repo = CostingEngineRunRepository()
        self.run_orchestrator = RunOrchestrator()
        self.async_task_service = AsyncTaskService()

    def get_ready(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineReadyVO:
        location_clean = LocationService().require_enabled(db, (location or "").strip())

        discovered = self.discovery.discover(db, location=location_clean, year=year, month=month)
        upload_or_config = self.gate_checker.check(db, discovered)
        annual_derived = self.annual_planner.plan(db, discovered)
        hard_stop = any(
            (not item.ok) and item.code not in SOFT_UPLOAD_GATE_CODES for item in upload_or_config
        )
        has_path = bool(discovered.stamping_vehicle_models or discovered.l0_scopes)
        can_start = (not hard_stop) and has_path

        plan = CostingEnginePlanVO(
            steel={
                "location": discovered.location,
                "year": discovered.year,
                "month": discovered.month,
            },
            part_cost_scopes=[
                CostingEnginePartCostScopeVO(vehicle_model=name)
                for name in discovered.stamping_vehicle_models
            ],
            l0_scopes=[
                CostingEngineL0ScopeVO(
                    vehicle_model=s.vehicle_model,
                    bom_version=s.bom_version,
                )
                for s in discovered.l0_scopes
            ],
        )
        return CostingEngineReadyVO(
            input={"location": location_clean, "year": year, "month": month},
            gates=CostingEngineGatesVO(
                hard_stop=hard_stop,
                upload_or_config=upload_or_config,
                annual_derived=annual_derived,
            ),
            plan=plan,
            can_start=can_start,
        )

    def start_run(
        self,
        db: Session,
        dto: CostingEngineRunCreateDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        ready = self.get_ready(db, location=dto.location, year=dto.year, month=dto.month)
        if not ready.can_start:
            raise CostingEngineHardStopError(
                "硬门禁未通过，无法启动引擎",
                upload_or_config=ready.gates.upload_or_config,
            )

        existing = self.run_repo.get_running_by_key(
            db,
            location=ready.input["location"],
            year=dto.year,
            month=dto.month,
        )
        if existing is not None:
            raise BusinessException(
                f"该基地 {dto.year}-{dto.month:02d} 已有进行中的引擎任务 "
                f"(run_id={existing.id})，请先删除后再启动"
            )

        audit = audit_create(current_user)
        task = self.async_task_service.create_task(
            task_type=TASK_TYPE_COSTING_ENGINE_RUN,
            message="月度核价引擎已入队",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        run = self.run_repo.create(
            db,
            location=str(ready.input["location"]),
            year=dto.year,
            month=dto.month,
            status="running",
            task_id=task.task_id,
            gate_json=cast(GateJson, ready.gates.model_dump(exclude_none=True)),
            plan_json=cast(PlanJson, ready.plan.model_dump()),
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
            started_at=now(),
        )
        db.commit()

        self._submit_run_worker(
            task.task_id,
            run.id,
            str(ready.input["location"]),
            dto.year,
            dto.month,
            current_user,
        )
        return AsyncTaskAcceptedVO(task_id=task.task_id)

    def get_task_progress(self, db: Session, task_id: str) -> AsyncTaskProgressVO:
        snapshot = self.async_task_service.get_task_snapshot(task_id)
        if snapshot is None:
            raise NotFoundException("任务不存在或已过期")
        if snapshot.get("task_type") != TASK_TYPE_COSTING_ENGINE_RUN:
            raise NotFoundException("任务类型不匹配")

        result = AsyncTaskService.parse_result_json(snapshot.get("result_json"))
        # 若 AsyncTask 过期但 Run 仍在，可从 Run 补终态
        if result is None:
            run = self.run_repo.get_by_task_id(db, task_id)
            if run is not None and run.status != "running":
                result = {
                    "run_id": run.id,
                    **(run.summary_json or {}),
                    "status": run.status,
                }
        return AsyncTaskProgressVO.from_snapshot(
            snapshot,
            default_status=STATUS_PENDING,
            result=result,
        )

    def get_run(self, db: Session, run_id: int) -> CostingEngineRunVO:
        run = self.run_repo.get_by_id(db, run_id)
        if run is None:
            raise NotFoundException(f"引擎 Run 不存在: {run_id}")
        return CostingEngineRunVO.model_validate(run)

    def list_runs(
        self,
        db: Session,
        *,
        location: str | None = None,
        year: int | None = None,
        month: int | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[CostingEngineRunListItemVO], int]:
        rows, total = self.run_repo.paginate(
            db,
            location=location,
            year=year,
            month=month,
            status=status,
            skip=(page - 1) * size,
            limit=size,
        )
        items = [CostingEngineRunListItemVO.model_validate(r) for r in rows]
        return items, total

    def delete_run(self, db: Session, run_id: int) -> None:
        run = self.run_repo.get_by_id(db, run_id)
        if run is None:
            raise NotFoundException(f"引擎 Run 不存在: {run_id}")
        task_id = run.task_id
        deleted = self.run_repo.delete(db, run_id)
        if not deleted:
            raise NotFoundException(f"引擎 Run 不存在: {run_id}")
        db.commit()
        if task_id:
            self._mark_task_deleted(task_id, run_id)

    def delete_all_runs(self, db: Session) -> DeletedCountVO:
        task_ids = self.run_repo.list_running_task_ids(db)
        deleted_count = self.run_repo.delete_all(db)
        db.commit()
        for task_id in task_ids:
            self._mark_task_deleted(task_id, run_id=None)
        return DeletedCountVO(deleted_count=deleted_count)

    def _mark_task_deleted(self, task_id: str, run_id: int | None) -> None:
        result: EngineWorkerResultJson = {"status": "deleted"}
        if run_id is not None:
            result["run_id"] = run_id
        try:
            self.async_task_service.update_task_standalone(
                task_id,
                status=STATUS_FAILED,
                progress=100,
                message="用户删除 Run",
                result=result,
            )
        except Exception:
            logger.exception("标记父任务失败可忽略: task_id=%s", task_id)

    def _submit_run_worker(
        self,
        task_id: str,
        run_id: int,
        location: str,
        year: int,
        month: int,
        current_user: UserVO,
    ) -> None:
        def work(db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            try:
                discovered = self.discovery.discover(db, location=location, year=year, month=month)
                annual_items = self.annual_planner.plan(db, discovered)
                summary = self.run_orchestrator.execute(
                    db,
                    run_id=run_id,
                    discovery=discovered,
                    annual_items=annual_items,
                    current_user=current_user,
                    progress_callback=on_progress,
                )
            except RunDeletedError:
                logger.info("引擎 Run 已删除，Worker 退出: run_id=%s", run_id)
                return WorkerTaskOutcome(
                    status=STATUS_FAILED,
                    progress=100,
                    message="用户删除 Run",
                    result={"run_id": run_id, "status": "deleted"},
                )
            run = self.run_repo.get_by_id(db, run_id)
            result_payload: EngineWorkerResultJson = {
                "run_id": run_id,
                **summary,
                **_run_timing_payload(
                    run.started_at if run is not None else None,
                    run.finished_at if run is not None else None,
                ),
            }
            parent_status = STATUS_COMPLETED
            if summary.get("status") == "failed":
                parent_status = STATUS_FAILED
            return WorkerTaskOutcome(
                status=parent_status,
                message=f"引擎结束 · {summary.get('status')}",
                result=result_payload,
            )

        crash_timing: EngineWorkerResultJson = {}

        def on_crash(db: Session, error: BaseException) -> None:
            nonlocal crash_timing
            try:
                run = self.run_repo.get_by_id(db, run_id)
                if run is not None:
                    finished_at = now()
                    crash_summary: SummaryJson = {
                        "status": "failed",
                        "location": location,
                        "year": year,
                        "month": month,
                        "steps": [],
                        "counts": {"succeeded": 0, "failed": 1, "skipped": 0},
                        "error": str(error),
                    }
                    self.run_repo.update_run_fields(
                        db,
                        run,
                        status="failed",
                        summary_json=crash_summary,
                        finished_at=finished_at,
                    )
                    db.commit()
                    crash_timing = _run_timing_payload(run.started_at, finished_at)
            except Exception:
                logger.exception("回写失败状态失败 run_id=%s", run_id)

        def crash_result(error: BaseException) -> EngineWorkerResultJson:
            payload: EngineWorkerResultJson = {
                "run_id": run_id,
                "status": "failed",
                "error": str(error),
                **crash_timing,
            }
            return payload

        self.async_task_service.submit_session_worker(
            task_id,
            start_message="引擎后台开始…",
            work=work,
            on_crash=on_crash,
            crash_message=lambda error: f"引擎失败: {error}",
            crash_progress=100,
            crash_result=crash_result,
        )
