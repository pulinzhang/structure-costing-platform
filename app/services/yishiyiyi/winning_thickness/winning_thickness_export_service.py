"""
中标钢厂厚度价格一览（门面）

行组装见 assemble；Excel 见 export。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.winning_thickness_vo import WinningThicknessRowVO
from app.services.yishiyiyi.winning_thickness.assemble.row_assembler import (
    WinningThicknessRowAssembler,
)
from app.services.yishiyiyi.winning_thickness.export.excel_exporter import (
    WinningThicknessExporter,
)

__all__ = ["WinningThicknessExportService"]


class WinningThicknessExportService:
    """
    中标钢厂厚度价格一览表：基价 × 大类厚度阶梯，含加工费。

    以基价表为据：仅当期有中标基价的牌号才输出。
    预览/导出均为「扁平行」：每个牌号按 CATEGORY 厚度政策展开全部区间，
    一行对应一个厚度阶梯（前端据此做阶梯展示）。
    """

    def __init__(self) -> None:
        self._assembler = WinningThicknessRowAssembler()
        self._exporter = WinningThicknessExporter()
        # 兼容直接读 repository 的用法
        self.base_repository = self._assembler.base_repository
        self.policy_repository = self._assembler.policy_repository
        self.grade_category_repository = self._assembler.grade_category_repository

    def build_rows(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
    ) -> list[WinningThicknessRowVO]:
        return self._assembler.build_rows(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            category_name=category_name,
            grade=grade,
        )

    def preview(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        page: int = 1,
        page_size: int = 500,
    ) -> tuple[list[WinningThicknessRowVO], int]:
        """预览：返回扁平行列表，每行一个厚度阶梯（同牌号多行）。"""
        all_rows = self.build_rows(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            category_name=category_name,
            grade=grade,
        )
        total = len(all_rows)
        page = max(page, 1)
        page_size = max(page_size, 1)
        start = (page - 1) * page_size
        return all_rows[start : start + page_size], total

    def export(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
    ) -> tuple[bytes, str]:
        rows = self.build_rows(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            category_name=category_name,
            grade=grade,
        )
        return self._exporter.generate(rows, year=year, month=month, location=location)
