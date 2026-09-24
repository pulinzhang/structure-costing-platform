"""材料变更上传入队壳。"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.timezone import now
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.engineering_change.material_change.codes import ECM_FILE_TYPE, ECM_PROJECT_PERIOD
from app.repositories.engineering_change.material_change.upload_log_repository import (
    MaterialChangeUploadLogInsert,
    MaterialChangeUploadLogRepository,
    MaterialChangeUploadLogUpdate,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_ENGINEERING_CHANGE_MATERIAL_UPLOAD,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import ProgressCallback, WorkerTaskOutcome
from app.services.engineering_change.material_change.upload.orchestrator.orchestrator import (
    MaterialChangeOrchestrator,
)
from app.services.engineering_change.material_change.upload.orchestrator.types import (
    MaterialChangeExecuteArgs,
)
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.masterdata.vehicle_model.service import VehicleModelService

logger = logging.getLogger("service.engineering_change.material_change.start_upload")

_FILE_CATEGORY = "engineering_change_material"
_log_repo = MaterialChangeUploadLogRepository()


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
    try:
        VehicleModelService().require_introducible(
            db, location, vehicle_model, effective_year, effective_month
        )
    except BusinessException as error:
        raise BusinessException(f"{ECM_PROJECT_PERIOD}。{error}") from error
    if not filename:
        raise BusinessException("没有选到文件。请先选择一份 .xlsx 再传。")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext != ".xlsx":
        raise BusinessException(f"{ECM_FILE_TYPE}。当前文件是{filename}。")
    if not file_content:
        raise BusinessException("文件是空的。请检查后再传。")
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        limit_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
        raise BusinessException(f"文件太大，最大 {limit_mb}MB。请删掉多余内容后再传。")

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
        MaterialChangeUploadLogInsert(
            upload_file_id=upload_file.id,
            location=location,
            vehicle_model=vehicle_model,
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
        task_type=TASK_TYPE_ENGINEERING_CHANGE_MATERIAL_UPLOAD,
        message="已提交材料变更解析队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    log_id = log_row.id
    refreshed = _log_repo.get_by_id(db, log_id)
    if refreshed is None:
        raise BusinessException("上传没有记上，请再传一次。")
    _log_repo.update(db, refreshed, MaterialChangeUploadLogUpdate(task_id=task.task_id))
    db.commit()

    def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
        orchestrator = MaterialChangeOrchestrator()
        try:
            result = orchestrator.execute(
                worker_db,
                MaterialChangeExecuteArgs(
                    log_id=log_id,
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
            logger.warning("材料变更上传业务失败: task_id=%s error=%s", task.task_id, error)
            worker_db.rollback()
            orchestrator.mark_log_failed(worker_db, log_id, str(error), current_user)
            return WorkerTaskOutcome(
                status=STATUS_FAILED,
                progress=0,
                message=str(error),
            )
        return WorkerTaskOutcome(
            status=STATUS_COMPLETED,
            message=f"材料变更成功：{len(result.order_ids)} 行切点",
            result=result.model_dump(),
        )

    def on_crash(worker_db: Session, error: BaseException) -> None:
        MaterialChangeOrchestrator().mark_log_failed(
            worker_db, log_id, f"材料变更异常: {error}", current_user
        )

    async_task_service.submit_session_worker(
        task.task_id,
        start_message="后台开始解析材料变更...",
        work=work,
        on_crash=on_crash,
        crash_message=lambda error: f"材料变更异常: {error}",
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
        / "engineering_change_material"
        / f"{effective_year}{effective_month:02d}"
    )
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{stamp}_{filename}"
    target.write_bytes(file_content)
    return target
