"""
钢价政策业务服务（门面）

CRUD / 导入 / 匹配 / 导出见各子包；本模块仅委托并保持对外 API。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.exceptions.base import BusinessException
from app.schemas.dto.steel_price_policy_dto import (
    LadderItemCreate,
    LadderItemUpdate,
    PolicyCreate,
    PolicyMatchRequest,
    PolicyQuery,
    PolicyUpdate,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.steel_price_policy_vo import (
    ExportRow,
    ImportResultResponse,
    LadderItemResponse,
    PolicyDetailResponse,
    PolicyListResponse,
    PolicyMatchResponse,
    PolicyOptionsResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_POLICY_UPLOAD,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import WorkerTaskOutcome
from app.services.yishiyiyi.policy.crud.service import SteelPricePolicyCrudService
from app.services.yishiyiyi.policy.export.service import (
    SteelPricePolicyExportService,
)
from app.services.yishiyiyi.policy.importing.service import (
    ProgressCallback,
    SteelPricePolicyImportService,
)
from app.services.yishiyiyi.policy.match.service import SteelPricePolicyMatchService

__all__ = [
    "ProgressCallback",
    "SteelPricePolicyService",
]

logger = logging.getLogger("service.steel_price_policy")


class SteelPricePolicyService:
    """钢价政策业务服务：委托 CRUD / 导入 / 匹配 / 导出。"""

    def __init__(self) -> None:
        self._crud = SteelPricePolicyCrudService()
        self._import_service = SteelPricePolicyImportService()
        self._match_service = SteelPricePolicyMatchService()
        self._export_service = SteelPricePolicyExportService()
        # 兼容 dashboard 等直接读 repository 的用法
        self.repository = self._crud.repository

    def paginate(
        self, db: Session, query: PolicyQuery
    ) -> tuple[list[PolicyListResponse], int, PolicyOptionsResponse]:
        return self._crud.paginate(db, query)

    def get_by_id(self, db: Session, policy_id: int) -> PolicyDetailResponse:
        return self._crud.get_by_id(db, policy_id)

    def create(
        self,
        db: Session,
        data: PolicyCreate,
        current_user: UserVO,
    ) -> PolicyDetailResponse:
        return self._crud.create(db, data, current_user)

    def update(
        self,
        db: Session,
        policy_id: int,
        data: PolicyUpdate,
        current_user: UserVO,
    ) -> PolicyDetailResponse:
        return self._crud.update(db, policy_id, data, current_user)

    def delete(self, db: Session, policy_id: int) -> None:
        return self._crud.delete(db, policy_id)

    def add_item(
        self,
        db: Session,
        policy_id: int,
        data: LadderItemCreate,
        current_user: UserVO,
    ) -> LadderItemResponse:
        return self._crud.add_item(db, policy_id, data, current_user)

    def update_item(
        self,
        db: Session,
        item_id: int,
        data: LadderItemUpdate,
        current_user: UserVO,
    ) -> LadderItemResponse:
        return self._crud.update_item(db, item_id, data, current_user)

    def delete_item(self, db: Session, item_id: int) -> None:
        return self._crud.delete_item(db, item_id)

    def match(self, db: Session, data: PolicyMatchRequest) -> PolicyMatchResponse:
        return self._match_service.match(db, data)

    def validate_upload(
        self,
        file_content: bytes,
        filename: str,
    ) -> None:
        self._import_service.validate_upload(file_content, filename)

    def build_template(self) -> tuple[bytes, str]:
        return self._import_service.build_template()

    def import_from_parser(
        self,
        db: Session,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
    ) -> ImportResultResponse:
        return self._import_service.import_from_parser(
            db,
            file_content,
            filename,
            year,
            month,
            current_user,
            progress_callback=progress_callback,
        )

    def get_export_data(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        sheet_name: str | None = None,
        category_name: str | None = None,
        grade_value: str | None = None,
        page: int = 1,
        size: int | None = None,
    ) -> list[ExportRow]:
        page = max(page, 1)
        skip = 0 if size is None else (page - 1) * size
        rows = self._export_service.get_export_data(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            sheet_name=sheet_name,
            category_name=category_name,
            grade_value=grade_value,
            skip=skip,
            limit=size,
        )
        return [ExportRow.model_validate(row.model_dump()) for row in rows]

    def count_export_data(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        sheet_name: str | None = None,
        category_name: str | None = None,
        grade_value: str | None = None,
    ) -> int:
        return self._export_service.count_export_data(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            sheet_name=sheet_name,
            category_name=category_name,
            grade_value=grade_value,
        )

    def count_policies(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        category_names: list[str] | None = None,
    ) -> int:
        return self._crud.count_policies(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            category_names=category_names,
        )

    def get_filter_options(self, db: Session) -> PolicyOptionsResponse:
        return self._crud.get_filter_options(db)

    def count_ladder_items(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        policy_type: str | None = None,
    ) -> int:
        return self._crud.count_ladder_items(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            policy_type=policy_type,
        )

    def generate_export_excel_bytes(
        self,
        db: Session,
        *,
        current_user: UserVO,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        sheet_name: str | None = None,
        category_name: str | None = None,
        grade_value: str | None = None,
    ) -> tuple[bytes, str]:
        return self._export_service.export_to_excel(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            sheet_name=sheet_name,
            category_name=category_name,
            grade_value=grade_value,
            current_user=current_user,
        )

    def list_sheet_names(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
    ) -> list[str]:
        return self._export_service.list_sheet_names(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
        )

    def delete_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        sheet_name: str | None = None,
    ) -> int:
        return self._crud.delete_by_conditions(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            sheet_name=sheet_name,
        )

    def start_upload(
        self,
        *,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        """创建异步任务并入队政策 Excel 解析。"""
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_POLICY_UPLOAD,
            message="已提交解析队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            try:
                result = self.import_from_parser(
                    db,
                    file_content=file_content,
                    filename=filename,
                    year=year,
                    month=month,
                    progress_callback=on_progress,
                    current_user=current_user,
                )
            except BusinessException as error:
                logger.warning("政策导入业务失败: task_id=%s error=%s", task.task_id, error)
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
