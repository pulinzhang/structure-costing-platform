"""
钢价政策业务服务（门面）

CRUD / 导入 / 匹配 / 导出见各子包；本模块仅委托并保持对外 API。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.yishiyiyi.policy.dto import ExportRow
from app.schemas.dto.steel_price_policy_dto import (
    LadderItemCreate,
    LadderItemUpdate,
    PolicyCreate,
    PolicyMatchRequest,
    PolicyQuery,
    PolicyUpdate,
)
from app.schemas.vo.steel_price_policy_vo import (
    ImportResultResponse,
    LadderItemResponse,
    PolicyDetailResponse,
    PolicyListResponse,
    PolicyMatchResponse,
    PolicyOptionsResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.yishiyiyi.policy.crud.policy_crud import SteelPricePolicyCrudService
from app.services.yishiyiyi.policy.export.export_service import (
    SteelPricePolicyExportService,
)
from app.services.yishiyiyi.policy.importing.import_service import (
    ProgressCallback,
    SteelPricePolicyImportService,
)
from app.services.yishiyiyi.policy.match.match_service import SteelPricePolicyMatchService

__all__ = [
    "ProgressCallback",
    "SteelPricePolicyService",
]


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

    def get_by_id(self, db: Session, policy_id: int) -> Optional[PolicyDetailResponse]:
        return self._crud.get_by_id(db, policy_id)

    def create(
        self,
        db: Session,
        data: PolicyCreate,
        current_user: UserVO,
    ) -> tuple[Optional[PolicyDetailResponse], Optional[str]]:
        return self._crud.create(db, data, current_user)

    def update(
        self,
        db: Session,
        policy_id: int,
        data: PolicyUpdate,
        current_user: UserVO,
    ) -> tuple[Optional[PolicyDetailResponse], Optional[str]]:
        return self._crud.update(db, policy_id, data, current_user)

    def delete(self, db: Session, policy_id: int) -> tuple[bool, Optional[str]]:
        return self._crud.delete(db, policy_id)

    def add_item(
        self,
        db: Session,
        policy_id: int,
        data: LadderItemCreate,
        current_user: UserVO,
    ) -> tuple[Optional[LadderItemResponse], Optional[str]]:
        return self._crud.add_item(db, policy_id, data, current_user)

    def update_item(
        self,
        db: Session,
        item_id: int,
        data: LadderItemUpdate,
        current_user: UserVO,
    ) -> tuple[Optional[LadderItemResponse], Optional[str]]:
        return self._crud.update_item(db, item_id, data, current_user)

    def delete_item(self, db: Session, item_id: int) -> tuple[bool, Optional[str]]:
        return self._crud.delete_item(db, item_id)

    def match(
        self, db: Session, data: PolicyMatchRequest
    ) -> PolicyMatchResponse:
        return self._match_service.match(db, data)

    def validate_upload(
        self,
        file_content: bytes,
        filename: str,
    ) -> None:
        self._import_service.validate_upload(file_content, filename)

    def import_from_parser(
        self,
        db: Session,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
        current_user: UserVO,
        progress_callback: Optional[ProgressCallback] = None,
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
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        category_name: Optional[str] = None,
        grade_value: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> list[ExportRow]:
        return self._export_service.get_export_data(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            category_name=category_name,
            grade_value=grade_value,
            skip=skip,
            limit=limit,
        )

    def count_export_data(
        self,
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        category_name: Optional[str] = None,
        grade_value: Optional[str] = None,
    ) -> int:
        return self._export_service.count_export_data(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            category_name=category_name,
            grade_value=grade_value,
        )

    def count_policies(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> int:
        return self._crud.count_policies(
            db, year=year, month=month, steel_mill=steel_mill
        )

    def get_filter_options(self, db: Session) -> PolicyOptionsResponse:
        return self._crud.get_filter_options(db)

    def count_ladder_items(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        policy_type: Optional[str] = None,
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
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        category_name: Optional[str] = None,
        grade_value: Optional[str] = None,
    ) -> tuple[bytes, str]:
        return self._export_service.export_to_excel(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            category_name=category_name,
            grade_value=grade_value,
        )

    def delete_by_conditions(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> tuple[int, Optional[str]]:
        return self._crud.delete_by_conditions(
            db, year=year, month=month, steel_mill=steel_mill
        )
