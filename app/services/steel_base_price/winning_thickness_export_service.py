"""中标材料厚度价格一览导出服务。

按基地 + 年 + 月，取该期中标基准价，匹配厚度加减价政策（钢厂别名与算价一致），
展开全部厚度区间，输出：最终价 = 基准价 + 加减价。
"""

from __future__ import annotations

import logging
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy.orm import Session

from app.models.steel_base_price import SteelBasePrice
from app.models.steel_price_policy import SteelPriceLadderItem, SteelPricePolicy
from app.repositories.steel_base_price import SteelBasePriceRepository
from app.repositories.steel_price_policy import SteelPricePolicyRepository
from app.schemas.vo.winning_thickness_vo import WinningThicknessRowVO
from app.services.steel_price.calc.models import CalcRow
from app.services.steel_price.calc.steps.adjustments.common import (
    filter_candidates,
    normalize_steel_mill,
    order_by_base_thickness,
)
from app.services.steel_price_policy.excel_exporter import format_interval

logger = logging.getLogger("service.winning_thickness_export")

# 与前端预览一致：弱化列 = 基地/钢种 + 溯源
_WEAK_COLS = frozenset({1, 9, 10})
_PRICE_COLS = frozenset({5, 6, 7, 8})

_HEADERS = [
    "基地/钢种",
    "牌号",
    "钢厂",
    "厚度范围",
    "基准价(元/吨)",
    "加减价(元/吨)",
    "加工费(元/吨)",
    "最终价(元/吨)",
    "基价溯源",
    "厚度溯源",
]

_COLUMN_WIDTHS = [18, 14, 12, 18, 14, 14, 14, 14, 36, 36]



class WinningThicknessExportService:
    """中标钢材各厚度价格一览（仅厚度加价）。"""

    def __init__(self) -> None:
        self.base_repository = SteelBasePriceRepository()
        self.policy_repository = SteelPricePolicyRepository()

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
        """组装一览行（必填：年/月/基地）。"""
        location = (location or "").strip()
        if not location:
            raise ValueError("基地不能为空")

        bases = self.base_repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill.strip() if steel_mill else None,
            category_name=category_name.strip() if category_name else None,
            grade=grade.strip() if grade else None,
        )
        policies = self.policy_repository.list_for_period(db, year=year, month=month)

        unique_bases = self._dedupe_bases(bases)
        rows: list[WinningThicknessRowVO] = []
        for base in unique_bases:
            rows.extend(self._expand_base(base, policies))

        rows.sort(
            key=lambda r: (
                r.location or "",
                r.category_name or "",
                r.grade or "",
                normalize_steel_mill(r.steel_mill),
                r.thickness_range or "",
            )
        )
        logger.info(
            "中标厚度一览组装完成: year=%s month=%s location=%s bases=%d rows=%d",
            year,
            month,
            location,
            len(unique_bases),
            len(rows),
        )
        return rows

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
        """预览分页。"""
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
        """生成 Excel 字节与文件名。"""
        rows = self.build_rows(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            category_name=category_name,
            grade=grade,
        )
        return self._write_excel(rows, year=year, month=month, location=location)

    # ------------------------------------------------------------------
    # 匹配与展开
    # ------------------------------------------------------------------

    @staticmethod
    def _dedupe_bases(bases: list[SteelBasePrice]) -> list[SteelBasePrice]:
        """同一牌号+钢厂+钢种只保留一条（列表已按钢厂/行列排序）。"""
        seen: set[tuple[str, str, str]] = set()
        result: list[SteelBasePrice] = []
        for base in bases:
            key = (
                (base.grade or "").strip(),
                normalize_steel_mill(base.steel_mill),
                (base.category_name or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(base)
        return result

    def _expand_base(
        self,
        base: SteelBasePrice,
        policies: list[SteelPricePolicy],
    ) -> list[WinningThicknessRowVO]:
        base_price = Decimal(str(base.base_price or 0))
        policy = self._find_best_thickness_policy(base, policies)
        if policy is None:
            return [self._make_row(base, base_price, Decimal("0"), "-", None, None)]

        items = [
            item
            for item in (policy.items or [])
            if item.thick_min is not None or item.thick_max is not None
        ]
        if not items:
            return [self._make_row(base, base_price, Decimal("0"), "-", policy, None)]

        items.sort(key=lambda x: (x.sort_order or 0, x.id or 0))
        rows: list[WinningThicknessRowVO] = []
        for item in items:
            adjustment = Decimal(str(item.price_adjustment or 0))
            thickness_range = format_interval(
                "t",
                item.thick_min,
                item.thick_min_operator,
                item.thick_max,
                item.thick_max_operator,
                decimals=2,
            )
            rows.append(
                self._make_row(
                    base,
                    base_price,
                    adjustment,
                    thickness_range,
                    policy,
                    item,
                )
            )
        return rows

    def _find_best_thickness_policy(
        self,
        base: SteelBasePrice,
        policies: list[SteelPricePolicy],
    ) -> SteelPricePolicy | None:
        """
        与算价 ThicknessAdjustmentMatcher 一致：
        - 钢厂别名 + 大类别名（filter_candidates）
        - 仅 THICKNESS，且 grade_value 精确等于牌号
        - 优先 base_thickness 一致
        """
        grade = (base.grade or "").strip()
        if not grade or not base.steel_mill or not base.category_name:
            return None

        calc_row = CalcRow(
            year=int(base.year),
            month=int(base.month),
            location=base.location or "",
            grade=grade,
            thickness=Decimal(str(base.thick)) if base.thick is not None else Decimal("0"),
            steel_mill=base.steel_mill,
            category_name=base.category_name,
            base_thickness=(
                Decimal(str(base.thick)) if base.thick is not None else None
            ),
            base_price=Decimal(str(base.base_price or 0)),
            base_price_id=base.id,
        )
        candidates = filter_candidates(calc_row, policies)
        thickness_policies = [
            p
            for p in candidates
            if p.policy_type == "THICKNESS"
            and (p.grade_value or "").strip() == grade
        ]
        if not thickness_policies:
            return None

        ordered = order_by_base_thickness(
            thickness_policies,
            calc_row,
            prefer_base_thickness=True,
        )
        return ordered[0] if ordered else None

    @staticmethod
    def _make_row(
        base: SteelBasePrice,
        base_price: Decimal,
        adjustment: Decimal,
        thickness_range: str,
        policy: SteelPricePolicy | None,
        item: SteelPriceLadderItem | None,
    ) -> WinningThicknessRowVO:
        processing_fee = Decimal(str(base.processing_fee or 0))
        final_price = base_price + adjustment + processing_fee
        return WinningThicknessRowVO(
            base_price=float(base_price),
            thickness_adjustment=float(adjustment),
            processing_fee=float(processing_fee),
            final_price=float(final_price),
            category_name=base.category_name or "",
            steel_mill=base.steel_mill or "",
            thickness_range=thickness_range,
            grade=base.grade or "",
            year=int(base.year),
            month=int(base.month),
            location=base.location or "",
            spec=base.spec,
            base_thickness=float(base.thick) if base.thick is not None else None,
            base_price_id=base.id,
            base_excel_filename=base.excel_filename,
            base_sheet_name=base.sheet_name,
            base_excel_row=base.excel_row,
            base_excel_col=base.excel_col,
            thickness_policy_id=policy.id if policy else None,
            thickness_ladder_item_id=item.id if item else None,
            thickness_excel_filename=policy.excel_filename if policy else None,
            thickness_excel_row=item.excel_row if item else None,
            thickness_excel_col=item.excel_col if item else None,
        )

    # ------------------------------------------------------------------
    # Excel（列与前端预览一致）
    # ------------------------------------------------------------------

    @staticmethod
    def _format_location_category(location: str | None, category_name: str | None) -> str:
        loc = (location or "").strip()
        cat = (category_name or "").strip()
        if loc and cat:
            return f"{loc} · {cat}"
        return loc or cat or ""

    @staticmethod
    def _format_base_trace(row: WinningThicknessRowVO) -> str:
        parts = []
        if row.base_price_id is not None:
            parts.append(f"ID:{row.base_price_id}")
        if row.base_excel_filename:
            parts.append(row.base_excel_filename)
        if row.base_sheet_name:
            parts.append(row.base_sheet_name)
        if row.base_excel_row is not None:
            parts.append(f"R{row.base_excel_row}")
        if row.base_excel_col is not None:
            parts.append(f"C{row.base_excel_col}")
        return " · ".join(parts)

    @staticmethod
    def _format_thickness_trace(row: WinningThicknessRowVO) -> str:
        parts = []
        if row.thickness_policy_id is not None:
            parts.append(f"P:{row.thickness_policy_id}")
        if row.thickness_ladder_item_id is not None:
            parts.append(f"L:{row.thickness_ladder_item_id}")
        if row.thickness_excel_filename:
            parts.append(row.thickness_excel_filename)
        if row.thickness_excel_row is not None:
            parts.append(f"R{row.thickness_excel_row}")
        if row.thickness_excel_col is not None:
            parts.append(f"C{row.thickness_excel_col}")
        return " · ".join(parts)

    def _write_excel(
        self,
        rows: list[WinningThicknessRowVO],
        *,
        year: int,
        month: int,
        location: str,
    ) -> tuple[bytes, str]:
        wb = Workbook()
        ws = wb.active
        ws.title = "中标厚度价格"

        header_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        weak_header_fill = PatternFill(start_color="8FAADC", end_color="8FAADC", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        data_font = Font(name="微软雅黑", size=10, color="000000")
        weak_font = Font(name="微软雅黑", size=8, color="808080")
        data_left = Alignment(horizontal="left", vertical="center")
        data_right = Alignment(horizontal="right", vertical="center")

        thin_border = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF"),
        )

        ws.append(_HEADERS)
        ws.row_dimensions[1].height = 28
        for col_idx in range(1, len(_HEADERS) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = weak_header_fill if col_idx in _WEAK_COLS else header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        for row_idx, row in enumerate(rows, start=2):
            values = [
                self._format_location_category(row.location, row.category_name),
                row.grade,
                row.steel_mill,
                row.thickness_range,
                row.base_price,
                row.thickness_adjustment,
                row.processing_fee,
                row.final_price,
                self._format_base_trace(row),
                self._format_thickness_trace(row),
            ]
            ws.append(values)
            fill = PatternFill(
                start_color="F2F2F2" if row_idx % 2 == 0 else "FFFFFF",
                end_color="F2F2F2" if row_idx % 2 == 0 else "FFFFFF",
                fill_type="solid",
            )
            for col_idx in range(1, len(values) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = thin_border
                cell.fill = fill
                cell.font = weak_font if col_idx in _WEAK_COLS else data_font
                cell.alignment = data_right if col_idx in _PRICE_COLS else data_left

        for col_idx, width in enumerate(_COLUMN_WIDTHS, start=1):
            letter = ws.cell(row=1, column=col_idx).column_letter
            ws.column_dimensions[letter].width = width

        ws.freeze_panes = "A2"

        filename = f"中标厚度价格_{year}年_{month}月_{location}.xlsx"
        output = BytesIO()
        wb.save(output)
        logger.info("导出中标厚度价格完成: filename=%s rows=%d", filename, len(rows))
        return output.getvalue(), filename
