"""核价引擎 — 编排唯一入口。"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.costing.engine.costing_engine_run_repository import (
    CostingEngineRunRepository,
)
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
    STATUS_RUNNING,
    TASK_TYPE_COSTING_ENGINE_RUN,
    AsyncTaskService,
)
from app.services.costing.engine.annual_calc_planner import AnnualCalcPlanner
from app.services.costing.engine.gate_checker import GateChecker
from app.services.costing.engine.run_orchestrator import RunDeletedError, RunOrchestrator
from app.services.costing.engine.scope_discovery import ScopeDiscovery

logger = logging.getLogger("service.costing.engine")

# 仍展示「去处理」提示，但不计入 hard_stop / 不阻断 can_start
_SOFT_UPLOAD_GATE_CODES = frozenset({"thickness_policy"})


class CostingEngineHardStopError(BusinessException):
    """硬门禁未通过；Router 可将 upload_or_config 放入 fail.data。"""

    def __init__(
        self,
        message: str,
        *,
        upload_or_config: list[CostingEngineGateItemVO],
    ):
        super().__init__(message=message, code=400)
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
        location_clean = (location or "").strip()
        if not location_clean:
            raise BusinessException("请指定生产基地")

        discovered = self.discovery.discover(
            db, location=location_clean, year=year, month=month
        )
        upload_or_config = self.gate_checker.check(db, discovered)
        annual_derived = self.annual_planner.plan(db, discovered)
        hard_stop = any(
            (not item.ok) and item.code not in _SOFT_UPLOAD_GATE_CODES
            for item in upload_or_config
        )
        has_path = bool(discovered.stamping_suppliers or discovered.l0_scopes)
        can_start = (not hard_stop) and has_path

        plan = CostingEnginePlanVO(
            steel={
                "location": discovered.location,
                "year": discovered.year,
                "month": discovered.month,
            },
            part_cost_scopes=[
                CostingEnginePartCostScopeVO(stamping_supplier=s)
                for s in discovered.stamping_suppliers
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
        ready = self.get_ready(
            db, location=dto.location, year=dto.year, month=dto.month
        )
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
            gate_json=ready.gates.model_dump(exclude_none=True),
            plan_json=ready.plan.model_dump(),
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
            started_at=now(),
        )
        db.commit()

        AsyncTaskService.submit(
            self._process_run_in_background,
            task.task_id,
            run.id,
            str(ready.input["location"]),
            dto.year,
            dto.month,
            current_user,
        )
        return AsyncTaskAcceptedVO(task_id=task.task_id)

    def get_task_progress(
        self, db: Session, task_id: str
    ) -> AsyncTaskProgressVO:
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
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[CostingEngineRunListItemVO], int]:
        rows, total = self.run_repo.paginate(
            db,
            location=location,
            year=year,
            month=month,
            status=status,
            skip=skip,
            limit=limit,
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
            try:
                self.async_task_service.update_task_standalone(
                    task_id,
                    status=STATUS_FAILED,
                    progress=100,
                    message="用户删除 Run",
                    result={"run_id": run_id, "status": "deleted"},
                )
            except Exception:
                logger.exception("标记父任务失败可忽略: task_id=%s", task_id)

    def _process_run_in_background(
        self,
        task_id: str,
        run_id: int,
        location: str,
        year: int,
        month: int,
        current_user: UserVO,
    ) -> None:
        from app.database import DatabaseConfig

        session_factory = DatabaseConfig.get_session_factory()
        db = session_factory()

        def on_progress(progress: int, msg: str) -> None:
            try:
                # 若 run 已删，后续 execute 会抛 RunDeletedError
                self.async_task_service.update_task_standalone(
                    task_id,
                    status=STATUS_RUNNING,
                    progress=progress,
                    message=msg,
                )
            except Exception:
                logger.debug("更新引擎进度失败 task_id=%s", task_id, exc_info=True)

        try:
            self.async_task_service.update_task_standalone(
                task_id,
                status=STATUS_RUNNING,
                progress=1,
                message="引擎后台开始…",
            )
            discovered = self.discovery.discover(
                db, location=location, year=year, month=month
            )
            annual_items = self.annual_planner.plan(db, discovered)
            summary = self.run_orchestrator.execute(
                db,
                run_id=run_id,
                discovery=discovered,
                annual_items=annual_items,
                current_user=current_user,
                progress_callback=on_progress,
            )
            result_payload: dict[str, Any] = {
                "run_id": run_id,
                **summary,
            }
            parent_status = STATUS_COMPLETED
            if summary.get("status") == "failed":
                parent_status = STATUS_FAILED
            self.async_task_service.update_task_standalone(
                task_id,
                status=parent_status,
                progress=100,
                message=f"引擎结束 · {summary.get('status')}",
                result=result_payload,
            )
        except RunDeletedError:
            logger.info("引擎 Run 已删除，Worker 退出: run_id=%s", run_id)
            try:
                self.async_task_service.update_task_standalone(
                    task_id,
                    status=STATUS_FAILED,
                    progress=100,
                    message="用户删除 Run",
                    result={"run_id": run_id, "status": "deleted"},
                )
            except Exception:
                pass
        except Exception as exc:
            logger.exception("引擎执行失败: run_id=%s", run_id)
            try:
                db.rollback()
            except Exception:
                pass
            try:
                run = self.run_repo.get_by_id(db, run_id)
                if run is not None:
                    self.run_repo.update_run_fields(
                        db,
                        run,
                        status="failed",
                        summary_json={
                            "status": "failed",
                            "location": location,
                            "year": year,
                            "month": month,
                            "steps": [],
                            "counts": {"succeeded": 0, "failed": 1, "skipped": 0},
                            "error": str(exc),
                        },
                        finished_at=now(),
                    )
                    db.commit()
            except Exception:
                logger.exception("回写失败状态失败 run_id=%s", run_id)
            self.async_task_service.update_task_standalone(
                task_id,
                status=STATUS_FAILED,
                progress=100,
                message=f"引擎失败: {exc}",
                result={
                    "run_id": run_id,
                    "status": "failed",
                    "error": str(exc),
                },
            )
        finally:
            db.close()
