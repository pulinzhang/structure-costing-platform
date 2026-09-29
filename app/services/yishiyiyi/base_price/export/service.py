"""钢材基准价格列表服务：查询扁平化 + 生成 Excel。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.export_filters import require_year_month_export_filters
from app.repositories.yishiyiyi.base_price.steel_base_price_repository import (
    SteelBasePriceRepository,
)
from app.schemas.vo.steel_base_price_vo import SteelBasePriceExportRow
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.steel_mill.service import SteelMillService
from app.services.yishiyiyi.base_price.export.excel_exporter import (
    SteelBasePriceExporter,
)


class SteelBasePriceExportService:
    """钢材基准价格列表业务。"""

    def __init__(self) -> None:
        self.repository = SteelBasePriceRepository()
        self._exporter = SteelBasePriceExporter()

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
        """导出预览数据（支持前端分页）。返回 (items, total)。"""
        skip = None
        limit = None
        if page is not None and page_size is not None:
            skip = (page - 1) * page_size
            limit = page_size

        category = category_name.strip() if category_name else None
        grade_value = grade.strip() if grade else None

        mill_id = SteelMillService().filter_id(db, steel_mill)
        records = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill_id=mill_id,
            category_name=category,
            grade=grade_value,
            spec=spec,
            skip=skip,
            limit=limit,
        )
        total = self.repository.count_for_export(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill_id=mill_id,
            category_name=category,
            grade=grade_value,
            spec=spec,
        )
        return [SteelBasePriceExportRow.model_validate(r) for r in records], total

    def export(
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
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        """
        生成基准价格 Excel 导出文件。

        Returns:
            (文件字节数据, 文件名)
        """
        category = category_name.strip() if category_name else None
        grade_value = grade.strip() if grade else None
        require_year_month_export_filters(year, month)
        records = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill_id=SteelMillService().filter_id(db, steel_mill),
            category_name=category,
            grade=grade_value,
            spec=spec,
        )
        return self._exporter.generate(
            records,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            current_user=current_user,
        )
