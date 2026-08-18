"""
钢材基准价格业务服务（门面）

CRUD / 导入 / 导出见各子包；本模块仅委托并保持对外 API。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.yishiyiyi import SteelBasePrice
from app.schemas.dto.steel_base_price_dto import (
    FilterOptions,
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.schemas.vo.steel_base_price_vo import (
    SteelBasePriceExportRow,
    SteelBasePriceImportResultResponse,
    SteelBasePriceResponse,
)
from app.schemas.vo.user_vo import UserVO
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


class SteelBasePriceService:
    """钢材基准价格：委托 CRUD / 导入 / 导出查询。"""

    def __init__(self) -> None:
        self._crud = SteelBasePriceCrudService()
        self._import_service = SteelBasePriceImportService()
        self._export_service = SteelBasePriceExportService()
        self.repository = self._crud.repository

    def get_filter_options(self, db: Session) -> FilterOptions:
        return self._crud.get_filter_options(db)

    def paginate(
        self,
        db: Session,
        query: SteelBasePriceQuery,
    ) -> tuple[list[SteelBasePriceResponse], int]:
        return self._crud.paginate(db, query)

    def get_by_id(self, db: Session, record_id: int) -> SteelBasePriceResponse | None:
        return self._crud.get_by_id(db, record_id)

    def create(
        self,
        db: Session,
        body: SteelBasePriceCreate,
        current_user: UserVO,
    ) -> tuple[SteelBasePriceResponse | None, str | None]:
        return self._crud.create(db, body, current_user)

    def update(
        self,
        db: Session,
        record_id: int,
        body: SteelBasePriceUpdate,
        current_user: UserVO,
    ) -> tuple[SteelBasePriceResponse | None, str | None]:
        return self._crud.update(db, record_id, body, current_user)

    def delete(self, db: Session, record_id: int) -> tuple[bool, str | None]:
        return self._crud.delete(db, record_id)

    def batch_delete(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str | None = None,
        steel_mill: str | None = None,
    ) -> tuple[bool, str | None]:
        return self._crud.batch_delete(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
        )

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
        current_user: UserVO,
        progress_callback: Optional[ProgressCallback] = None,
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
        return self._crud.list_for_calc(
            db, year=year, month=month, location=location
        )

    def count_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        steel_mill: str | None = None,
        spec: str | None = None,
    ) -> int:
        return self._crud.count_by_conditions(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            spec=spec,
        )
