"""
钢材基准价格业务服务（门面）

CRUD / 导入 / 导出见各子包；本模块仅委托并保持对外 API。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.config import settings
from app.exceptions.base import BusinessException
from app.models.yishiyiyi import SteelBasePrice
from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.steel_base_price_vo import (
    SteelBasePriceExportRow,
    SteelBasePriceFilterOptionsVO,
    SteelBasePriceImportResultResponse,
    SteelBasePriceResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_BASE_PRICE_IMPORT,
    AsyncTaskService,
    WorkerTaskOutcome,
)
from app.services.yishiyiyi.base_price.crud.base_price_crud import (
    SteelBasePriceCrudService,
)
from app.services.yishiyiyi.base_price.export.export_service import (
    SteelBasePriceExportService,
)
from app.services.yishiyiyi.base_price.importing.import_service import (
    ProgressCallback,
    SteelBasePriceImportService,
)

__all__ = [
    "ProgressCallback",
    "SteelBasePriceService",
]

logger = logging.getLogger("service.steel_base_price")


class SteelBasePriceService:
    """钢材基准价格：委托 CRUD / 导入 / 导出查询。"""

    def __init__(self) -> None:
        self._crud = SteelBasePriceCrudService()
        self._import_service = SteelBasePriceImportService()
        self._export_service = SteelBasePriceExportService()
        self.repository = self._crud.repository

    def get_filter_options(self, db: Session) -> SteelBasePriceFilterOptionsVO:
        return self._crud.get_filter_options(db)

    def paginate(
        self,
        db: Session,
        query: SteelBasePriceQuery,
    ) -> tuple[list[SteelBasePriceResponse], int]:
        return self._crud.paginate(db, query)

    def get_by_id(self, db: Session, record_id: int) -> SteelBasePriceResponse:
        return self._crud.get_by_id(db, record_id)

    def create(
        self,
        db: Session,
        body: SteelBasePriceCreate,
        current_user: UserVO,
    ) -> SteelBasePriceResponse:
        return self._crud.create(db, body, current_user)

    def update(
        self,
        db: Session,
        record_id: int,
        body: SteelBasePriceUpdate,
        current_user: UserVO,
    ) -> SteelBasePriceResponse:
        return self._crud.update(db, record_id, body, current_user)

    def delete(self, db: Session, record_id: int) -> None:
        return self._crud.delete(db, record_id)

    def batch_delete(
        self,
        db: Session,
        *,
        year: int | None,
        month: int | None,
        location: str | None = None,
        steel_mill: str | None = None,
    ) -> tuple[int, int]:
        if year is None or month is None:
            raise BusinessException("year 和 month 不能为空")
        self._crud.batch_delete(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
        )
        return year, month

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
    ) -> SteelBasePriceImportResultResponse:
        return self._import_service.import_excel(
            db,
            file_content=file_content,
            filename=filename,
            year=year,
            month=month,
            current_user=current_user,
            progress_callback=progress_callback,
        )

    def build_template(self) -> tuple[bytes, str]:
        return self._import_service.build_template()

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        spec: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[SteelBasePriceExportRow], int]:
        return self._export_service.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            category_name=category_name,
            grade=grade,
            spec=spec,
            page=page,
            page_size=page_size,
        )

    def list_for_calc(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ) -> list[SteelBasePrice]:
        return self._crud.list_for_calc(db, year=year, month=month, location=location)

    def count_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        steel_mill: str | None = None,
        spec: str | None = None,
        grades_in: list[str] | None = None,
    ) -> int:
        return self._crud.count_by_conditions(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            spec=spec,
            grades_in=grades_in,
        )

    def start_import(
        self,
        *,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        """创建异步任务并入队基准价 Excel 解析。"""
        if not filename:
            raise BusinessException("未提供文件名")
        ext = "." + filename.split(".")[-1].lower()
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
            task_type=TASK_TYPE_BASE_PRICE_IMPORT,
            message="已提交解析队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            try:
                result = self.import_excel(
                    db,
                    file_content=file_content,
                    filename=filename,
                    year=year,
                    month=month,
                    progress_callback=on_progress,
                    current_user=current_user,
                )
            except BusinessException as error:
                logger.warning("基准价导入业务失败: task_id=%s error=%s", task.task_id, error)
                return WorkerTaskOutcome(
                    status=STATUS_FAILED,
                    progress=0,
                    message=str(error),
                )
            return WorkerTaskOutcome(
                status=STATUS_COMPLETED,
                message=(
                    f"导入完成：新增 {result.created_count} 条，"
                    f"更新 {result.updated_count} 条，共 {result.total} 条"
                ),
                result=result.model_dump(),
            )

        async_task_service.submit_session_worker(
            task.task_id,
            start_message="后台开始解析...",
            work=work,
            crash_message=lambda error: f"解析异常: {error}",
        )
        return AsyncTaskAcceptedVO(task_id=task.task_id)
