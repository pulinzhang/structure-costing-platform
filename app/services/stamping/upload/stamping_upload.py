"""
冲压工艺上传服务（门面，符号路径保持不变）。

处理 Excel 解析、文件保存、简图保存、数据库存储等业务逻辑。
主数据写入使用单一大事务；进度写入辅助库。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.tailor_weld import TailorWeldAssemblyParsed
from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.dto.stamping_upload_dto import UploadResult
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_STAMPING_UPLOAD,
    AsyncTaskService,
    WorkerTaskOutcome,
)
from app.services.stamping.tailor_weld_blank_service import StampingTailorWeldBlankService
from app.services.stamping.upload.cost_ratio_preserver import ProcessCostRatioPreserver
from app.services.stamping.upload.orchestrate import process_upload as run_process_upload
from app.services.stamping.upload.persist import canonicalize_materials
from app.services.stamping.upload.template_builder import build_stamping_process_template

# progress_callback(progress: int, msg: str)
ProgressCallback = Callable[[int, str], None]

logger = logging.getLogger("service.stamping_upload")


class StampingUploadService:
    """冲压工艺上传服务"""

    def __init__(self, db: Session):
        self.db = db
        self.part_repo = StampingPartRepository()
        self.process_repo = StampingProcessRepository()
        self.cost_ratio_preserver = ProcessCostRatioPreserver()
        self.tailor_weld_service = StampingTailorWeldBlankService()

    @staticmethod
    def build_template() -> tuple[bytes, str]:
        """下载用冲压工艺导入模板（含样例零件）。"""
        return build_stamping_process_template()

    def process_upload(
        self,
        file_content: bytes,
        filename: str,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
    ) -> UploadResult:
        return run_process_upload(
            self.db,
            part_repo=self.part_repo,
            process_repo=self.process_repo,
            cost_ratio_preserver=self.cost_ratio_preserver,
            tailor_weld_service=self.tailor_weld_service,
            file_content=file_content,
            filename=filename,
            current_user=current_user,
            progress_callback=progress_callback,
        )

    def _canonicalize_materials(
        self,
        parts: list[Part],
        assemblies: list[TailorWeldAssemblyParsed],
    ) -> None:
        canonicalize_materials(self.db, parts, assemblies)

    @classmethod
    def start_upload(
        cls,
        *,
        file_content: bytes,
        filename: str,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        """创建异步任务并入队；后台线程开独立 Session 解析入库。"""
        if not filename:
            raise BusinessException("未提供文件名")
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in {".xlsx", ".xls"}:
            raise BusinessException(f"不支持的文件类型: {ext}，仅支持 .xlsx / .xls")
        if not file_content:
            raise BusinessException("上传文件为空")
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            raise BusinessException(
                f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
            )

        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_STAMPING_UPLOAD,
            message="已提交解析队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            service = cls(db)
            try:
                result = service.process_upload(
                    file_content=file_content,
                    filename=filename,
                    progress_callback=on_progress,
                    current_user=current_user,
                )
            except (BusinessException, ValueError) as error:
                logger.warning("冲压上传业务失败: task_id=%s error=%s", task.task_id, error)
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
