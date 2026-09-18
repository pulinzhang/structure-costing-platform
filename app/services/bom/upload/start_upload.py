"""材料清单上传入队壳。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.exceptions.base import BusinessException
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_BOM_UPLOAD,
    AsyncTaskService,
    WorkerTaskOutcome,
)
from app.services.async_task.worker_runner import ProgressCallback
from app.services.bom.upload.gates.validate import validate_upload_file
from app.services.bom.upload.orchestrator import BomUploadOrchestrator
from app.services.bom.upload.orchestrator.types import BomUploadExecuteArgs

logger = logging.getLogger("service.bom.upload")


def start_upload(
    *,
    file_content: bytes,
    filename: str,
    location: str,
    vehicle_model: str,
    current_user: UserVO,
) -> AsyncTaskAcceptedVO:
    """校验表单与文件后 create_task + submit_session_worker。"""
    location = (location or "").strip()
    vehicle_model = (vehicle_model or "").strip()
    if not location:
        raise BusinessException("请选择采购基地")
    if not vehicle_model:
        raise BusinessException("请选择项目")
    validate_upload_file(filename=filename, file_content=file_content)

    async_task_service = AsyncTaskService()
    task = async_task_service.create_task(
        task_type=TASK_TYPE_BOM_UPLOAD,
        message="已提交材料清单解析队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )

    def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
        orchestrator = BomUploadOrchestrator()
        try:
            result = orchestrator.execute(
                worker_db,
                BomUploadExecuteArgs(
                    file_content=file_content,
                    filename=filename,
                    location=location,
                    vehicle_model=vehicle_model,
                ),
                current_user,
                on_progress=on_progress,
            )
        except (BusinessException, ValueError) as error:
            logger.warning("材料清单上传业务失败: task_id=%s error=%s", task.task_id, error)
            # 必须先 rollback：管线只 flush，若不回滚会把半截节点跟失败任务一起落库。
            worker_db.rollback()
            return WorkerTaskOutcome(
                status=STATUS_FAILED,
                progress=0,
                message=str(error),
            )
        return WorkerTaskOutcome(
            status=STATUS_COMPLETED,
            message=result.message,
            result=result.model_dump(mode="json"),
        )

    async_task_service.submit_session_worker(
        task.task_id,
        start_message="后台开始解析材料清单...",
        work=work,
        crash_message=lambda error: f"材料清单解析异常: {error}",
    )
    return AsyncTaskAcceptedVO(task_id=task.task_id)
