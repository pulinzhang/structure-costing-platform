"""牌号分类档案 Excel 导出。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.repositories.masterdata.steel_grade_category.steel_grade_category_repository import (
    SteelGradeCategoryRepository,
)
from app.schemas.dto.steel_grade_category_dto import SteelGradeCategoryExportQuery
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.steel_grade_category.catalog import (
    export_excel as export_catalog_excel,
)

logger = logging.getLogger("service.steel_grade_category.export")


class SteelGradeCategoryExportService:
    """按当前筛选导出牌号分类档案（核心列可再导入）。"""

    def __init__(self) -> None:
        self.repository = SteelGradeCategoryRepository()

    def export(
        self,
        db: Session,
        query: SteelGradeCategoryExportQuery,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        content, filename = export_catalog_excel(
            self.repository,
            db,
            current_user,
            grade=query.grade,
            category_name=query.category_name,
        )
        logger.info("导出牌号分类 -> %s", filename)
        return content, filename
