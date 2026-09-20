"""冲压工艺上传入队壳。"""

from __future__ import annotations

import logging
from dataclasses import asdict

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.exceptions.base import BusinessException
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.async_task_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_STAMPING_UPLOAD,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import ProgressCallback, WorkerTaskOutcome
from app.services.stamping.part.upload.gates.validate import validate_upload_file
from app.services.stamping.part.upload.orchestrator.orchestrator import StampingUploadOrchestrator
from app.services.stamping.part.upload.orchestrator.types import StampingUploadExecuteArgs

logger = logging.getLogger("service.stamping_upload")


def start_upload(
    *,
    file_content: bytes,
    filename: str,
    current_user: UserVO,
) -> AsyncTaskAcceptedVO:
    """校验文件后 create_task + submit_session_worker。"""
    validate_upload_file(filename=filename, file_content=file_content)

    async_task_service = AsyncTaskService()
    task = async_task_service.create_task(
        task_type=TASK_TYPE_STAMPING_UPLOAD,
        message="已提交解析队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )

    def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
        orchestrator = StampingUploadOrchestrator()
        try:
            result = orchestrator.execute(
                worker_db,
                StampingUploadExecuteArgs(
                    file_content=file_content,
                    filename=filename,
                ),
                current_user,
                on_progress=on_progress,
            )
        except (BusinessException, ValueError) as error:
            logger.warning("冲压上传业务失败: task_id=%s error=%s", task.task_id, error)
            # 必须先 rollback：管线只 flush，若不回滚会把半截零件跟失败任务一起落库。
            worker_db.rollback()
            return WorkerTaskOutcome(
                status=STATUS_FAILED,
                progress=0,
                message=str(error),
            )
        return WorkerTaskOutcome(
            status=STATUS_COMPLETED,
            message=(
                f"上传成功：{result.parts_count} 个零件，"
                f"{result.processes_count} 道工序"
                f"（拼焊 {result.tailor_weld_assembly_count} 件 / "
                f"{result.tailor_weld_blank_count} 片）"
            ),
            result=asdict(result),
        )

    async_task_service.submit_session_worker(
        task.task_id,
        start_message="后台开始解析...",
        work=work,
        crash_message=lambda error: f"解析异常: {error}",
    )
    return AsyncTaskAcceptedVO(task_id=task.task_id)
