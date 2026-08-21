"""
异步任务 Service。

进度落在辅助库（AuxiliaryDatabaseConfig，无 Redis 时的旁路存储）：
- 与主业务库物理隔离，不受业务长事务写锁影响
- 写入使用独立 AUTOCOMMIT 连接，每次立即生效（类 Redis 可见性）
- 无进程内存态，多 worker 轮询一致

分层：Service 管连接策略 / 节流 / 线程池；SQL 经 AsyncTaskRepository。
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.database import AuxiliaryDatabaseConfig
from app.models.async_task import AsyncTask
from app.repositories.async_task import AsyncTaskRepository
from app.repositories.persist import model_from_payload
from app.schemas.dto.async_task_dto import AsyncTaskInsert, AsyncTaskPatch
from app.utils.logging_config import get_logger


logger = get_logger("service.async_task")

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

TASK_TYPE_POLICY_UPLOAD = "steel_price_policy_upload"
TASK_TYPE_STAMPING_UPLOAD = "stamping_upload"
TASK_TYPE_BASE_PRICE_IMPORT = "steel_base_price_import"
TASK_TYPE_STEEL_PRICE_CALC = "steel_price_calc"
TASK_TYPE_STAMPING_PROCESS_FEE_CALC = "stamping_process_fee_calc"
TASK_TYPE_STAMPING_PART_COST_CALC = "stamping_part_cost_calc"
TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE = (
    "bom_welding_process_breakdown_generate"
)
TASK_TYPE_BOM_L0_WELDING_FEE_CALC = "bom_l0_welding_fee_calc"
TASK_TYPE_L0_ASSEMBLY_COST_CALC = "l0_assembly_cost_calc"
TASK_TYPE_COSTING_ENGINE_RUN = "costing_engine_run"

TASK_TTL_SECONDS = 3600

_PROGRESS_MIN_INTERVAL_SECONDS = 1.0
_PROGRESS_MIN_DELTA = 3

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="async-task")
_progress_throttle_lock = threading.Lock()
_progress_throttle_state: dict[str, tuple[float, int]] = {}


class AsyncTaskService:
    """异步任务业务逻辑（辅助库，多 worker 安全）。"""

    def __init__(self) -> None:
        self.repository = AsyncTaskRepository()

    def _autocommit_connection(self) -> Any:
        """辅助库独立连接 + AUTOCOMMIT（进度立即对轮询可见）。"""
        engine = AuxiliaryDatabaseConfig.get_engine()
        return engine.connect().execution_options(isolation_level="AUTOCOMMIT")

    def _read_session(self) -> Session:
        """短生命周期只读 Session（查询进度）。"""
        return AuxiliaryDatabaseConfig.get_session_factory()()

    def _should_skip_db_write(
        self,
        task_id: str,
        *,
        status: Optional[str],
        progress: Optional[int],
        result: Any,
    ) -> bool:
        if status in (STATUS_COMPLETED, STATUS_FAILED) or result is not None:
            with _progress_throttle_lock:
                _progress_throttle_state.pop(task_id, None)
            return False
        now_ts = time.time()
        prog = 0 if progress is None else int(progress)
        with _progress_throttle_lock:
            last = _progress_throttle_state.get(task_id)
            if last is not None:
                last_ts, last_prog = last
                if (
                    now_ts - last_ts < _PROGRESS_MIN_INTERVAL_SECONDS
                    and abs(prog - last_prog) < _PROGRESS_MIN_DELTA
                    and prog < 100
                ):
                    return True
            _progress_throttle_state[task_id] = (now_ts, prog)
        return False

    def create_task(
        self,
        *,
        task_type: str,
        message: str = "已提交解析队列",
        operator_id: int | None = None,
        operator_name: str | None = None,
    ) -> AsyncTask:
        """创建 pending 任务（写入辅助库）。"""
        self.clean_expired_tasks()
        task_id = str(uuid.uuid4())
        current_time = now()
        payload = AsyncTaskInsert(
            task_id=task_id,
            task_type=task_type,
            status=STATUS_PENDING,
            progress=0,
            message=message,
            result_json=None,
            operator_id=operator_id,
            operator_name=operator_name,
            created_by=operator_name,
            updated_by=operator_name,
            created_at=current_time,
            updated_at=current_time,
        )
        with self._autocommit_connection() as conn:
            self.repository.insert_task(conn, payload)
        return model_from_payload(AsyncTask, payload)

    def get_by_task_id(self, task_id: str) -> Optional[AsyncTask]:
        db = self._read_session()
        try:
            return self.repository.get_by_task_id(db, task_id)
        finally:
            db.close()

    def get_task_snapshot(self, task_id: str) -> Optional[dict[str, Any]]:
        """轮询快照：只读辅助库。"""
        record = self.get_by_task_id(task_id)
        if record is None:
            return None
        return {
            "task_id": record.task_id,
            "task_type": record.task_type,
            "status": record.status,
            "progress": int(record.progress or 0),
            "message": record.message or "",
            "result_json": record.result_json,
            "operator_id": record.operator_id,
            "operator_name": record.operator_name,
            "updated_at": record.updated_at,
        }

    def update_task(
        self,
        task_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Any = None,
    ) -> None:
        """AUTOCOMMIT 更新任务（辅助库）。"""
        values: AsyncTaskPatch = {"updated_at": now()}
        if status is not None:
            values["status"] = status
        if progress is not None:
            values["progress"] = max(0, min(100, int(progress)))
        if message is not None:
            values["message"] = message[:500]
        if result is not None:
            values["result_json"] = json.dumps(result, ensure_ascii=False)

        with self._autocommit_connection() as conn:
            self.repository.update_by_task_id(conn, task_id, values)

    def update_task_standalone(
        self,
        task_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Any = None,
    ) -> None:
        """后台线程专用：写入辅助库。"""
        if self._should_skip_db_write(
            task_id, status=status, progress=progress, result=result
        ):
            return

        try:
            self.update_task(
                task_id,
                status=status,
                progress=progress,
                message=message,
                result=result,
            )
        except Exception:
            if status in (STATUS_COMPLETED, STATUS_FAILED):
                logger.exception("更新异步任务终态失败: task_id=%s", task_id)
            else:
                logger.debug("异步任务进度写库失败: task_id=%s", task_id)

    def clean_expired_tasks(self) -> int:
        """清理过期任务（辅助库 AUTOCOMMIT）。"""
        cutoff = now() - timedelta(seconds=TASK_TTL_SECONDS)
        with self._autocommit_connection() as conn:
            count = self.repository.delete_older_than(conn, cutoff)
        if count:
            logger.info("清理过期异步任务: count=%s", count)
        return count

    @staticmethod
    def parse_result_json(result_json: Optional[str]) -> Any:
        if not result_json:
            return None
        try:
            return json.loads(result_json)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def submit(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        _executor.submit(fn, *args, **kwargs)
