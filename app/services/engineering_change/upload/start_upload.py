"""工程变更上传入队壳。"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.timezone import now
from app.config import settings
from app.exceptions.base import BusinessException
from app.repositories.engineering_change.upload_log_repository import (
    EngineeringChangeUploadLogInsert,
    EngineeringChangeUploadLogRepository,
    EngineeringChangeUploadLogUpdate,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    AsyncTaskService,
    WorkerTaskOutcome,
)
from app.services.async_task.async_task_service import TASK_TYPE_ENGINEERING_CHANGE_UPLOAD
from app.services.async_task.worker_runner import ProgressCallback
from app.services.engineering_change.upload.orchestrator import EngineeringChangeOrchestrator
from app.services.engineering_change.upload.orchestrator.types import (
    EngineeringChangeExecuteArgs,
)
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.masterdata.vehicle_model import VehicleModelService

logger = logging.getLogger("service.engineering_change.start_upload")

_FILE_CATEGORY = "engineering_change"
_log_repo = EngineeringChangeUploadLogRepository()


def start_upload(
    db: Session,
    *,
    file_content: bytes,
    filename: str,
    location: str,
    vehicle_model: str,
    effective_year: int,
    effective_month: int,
    current_user: UserVO,
) -> AsyncTaskAcceptedVO:
    """落盘存档 → pending 日志 → create_task + submit_session_worker。"""
    location, vehicle_model = VehicleModelService().require_introducible(
        db,
        (location or "").strip(),
        (vehicle_model or "").strip(),
        effective_year,
        effective_month,
    )
    if not filename:
        raise BusinessException("未提供文件名")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {".xlsx", ".xls"}:
        raise BusinessException(f"不支持的文件类型: {ext}，仅支持 .xlsx / .xls")
    if not file_content:
        raise BusinessException("上传文件为空")
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        raise BusinessException(f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB")

    stored_path = _save_file(
        file_content, filename, location, vehicle_model, effective_year, effective_month
    )
    upload_file = register_existing(
        db,
        file_category=_FILE_CATEGORY,
        stored_relpath=to_upload_relpath(stored_path),
        original_filename=filename,
        current_user=current_user,
        location=location,
        vehicle_model=vehicle_model,
        year=effective_year,
        month=effective_month,
        supersede_same_scope=False,
    )
    audit = audit_create(current_user)
    log_row = _log_repo.create(
        db,
        EngineeringChangeUploadLogInsert(
            upload_file_id=upload_file.id,
            location=location,
            vehicle_model=vehicle_model,
            customer_name="",
            effective_year=effective_year,
            effective_month=effective_month,
            original_filename=filename,
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
            status="pending",
        ),
    )
    db.commit()

    async_task_service = AsyncTaskService()
    task = async_task_service.create_task(
        task_type=TASK_TYPE_ENGINEERING_CHANGE_UPLOAD,
        message="已提交工程变更解析队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    log_id = log_row.id
    refreshed = _log_repo.get_by_id(db, log_id)
    if refreshed is None:
        raise BusinessException("工程变更上传记录写入后丢失")
    _log_repo.update(db, refreshed, EngineeringChangeUploadLogUpdate(task_id=task.task_id))
    db.commit()

    upload_file_id = upload_file.id

    def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
        orchestrator = EngineeringChangeOrchestrator()
        try:
            result = orchestrator.execute(
                worker_db,
                EngineeringChangeExecuteArgs(
                    log_id=log_id,
                    upload_file_id=upload_file_id,
                    location=location,
                    vehicle_model=vehicle_model,
                    effective_year=effective_year,
                    effective_month=effective_month,
                    file_content=file_content,
                ),
                current_user,
                on_progress=on_progress,
            )
        except (BusinessException, ValueError) as error:
            logger.warning("工程变更上传业务失败: task_id=%s error=%s", task.task_id, error)
            # 必须先 rollback：管线只 flush，若不回滚就 mark_log_failed→commit，
            # 半截种树/工艺会跟 failed 日志一起落库，旧月 AA 与脏 AB 并存。
            worker_db.rollback()
            orchestrator.mark_log_failed(worker_db, log_id, str(error), current_user)
            return WorkerTaskOutcome(
                status=STATUS_FAILED,
                progress=0,
                message=str(error),
            )
        return WorkerTaskOutcome(
            status=STATUS_COMPLETED,
            message=f"工程变更成功：{len(result.change_order_ids)} 行变更单",
            result=result.model_dump(),
        )

    def on_crash(worker_db: Session, error: BaseException) -> None:
        EngineeringChangeOrchestrator().mark_log_failed(
            worker_db, log_id, f"工程变更异常: {error}", current_user
        )

    async_task_service.submit_session_worker(
        task.task_id,
        start_message="后台开始解析工程变更...",
        work=work,
        on_crash=on_crash,
        crash_message=lambda error: f"工程变更异常: {error}",
    )
    return AsyncTaskAcceptedVO(task_id=task.task_id)


def _save_file(
    file_content: bytes,
    filename: str,
    location: str,
    vehicle_model: str,
    effective_year: int,
    effective_month: int,
) -> Path:
    safe_location = location.replace("/", "_").replace("\\", "_")
    safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
    stamp = now().strftime("%Y%m%d_%H%M%S")
    folder = (
        settings.UPLOAD_DIR
        / safe_location
        / safe_vehicle
        / "engineering_change"
        / f"{effective_year}{effective_month:02d}"
    )
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{stamp}_{filename}"
    target.write_bytes(file_content)
    return target
