"""冲次单价 Excel 导入 / 模板下载服务。"""

from __future__ import annotations

import logging
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.parsers.stamping.tonnage_price_parser import parse_tonnage_price_excel
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.schemas.vo.stamping_tonnage_price_vo import StampingTonnagePriceImportResultVO
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.stamping_tonnage_price_import")

TEMPLATE_SAMPLE_ROWS = [
    ("400T", "次", 0.564),
    ("500T", "次", 0.622),
    ("630T", "次", 0.713),
    ("800T", "次", 1.026),
    ("1000T", "次", 1.283),
    ("1200T", "次", 1.539),
]


class StampingTonnagePriceImportService:
    """冲次单价同步导入（数据量小，不走异步任务）。"""

    def __init__(self) -> None:
        self.repository = StampingTonnagePriceRepository()

    def build_template(self) -> tuple[bytes, str]:
        """生成三列模板：名称 / 单位 / 单价。"""
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "冲次单价"

        header_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        data_font = Font(name="微软雅黑", size=9)
        thin_border = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF"),
        )

        headers = ["名称", "单位", "单价"]
        for col, title in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=col, value=title)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        for row_idx, (name, unit, price) in enumerate(TEMPLATE_SAMPLE_ROWS, start=2):
            values = [name, unit, price]
            for col, value in enumerate(values, start=1):
                cell = sheet.cell(row=row_idx, column=col, value=value)
                cell.font = data_font
                cell.border = thin_border
                cell.alignment = Alignment(
                    horizontal="center" if col < 3 else "right",
                    vertical="center",
                )
                if col == 3:
                    cell.number_format = "0.000"

        sheet.column_dimensions["A"].width = 12
        sheet.column_dimensions["B"].width = 10
        sheet.column_dimensions["C"].width = 12
        sheet.freeze_panes = "A2"

        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue(), "冲次单价导入模板.xlsx"

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        location: str,
        year: int,
        current_user: UserVO,
    ) -> StampingTonnagePriceImportResultVO:
        location = (location or "").strip()
        if not location:
            raise ValueError("请选择采购基地")
        if year < 2000 or year > 2100:
            raise ValueError("年度不正确")

        original_name = Path(filename or "").name
        if Path(original_name).suffix.lower() != ".xlsx":
            raise ValueError("仅支持 .xlsx 文件")
        if not file_content:
            raise ValueError("文件内容为空")

        parse_result = parse_tonnage_price_excel(file_content)
        if parse_result.errors and not parse_result.rows:
            raise ValueError("；".join(parse_result.errors))
        if not parse_result.rows:
            raise ValueError("未解析到有效数据行")

        created_count = 0
        updated_count = 0
        create_audit = audit_create(current_user)
        update_audit = audit_update(current_user)

        try:
            for row in parse_result.rows:
                price = Decimal(str(row.price_per_stroke))
                existing = self.repository.get_by_location_year_tonnage(
                    db, location, year, row.tonnage
                )
                if existing:
                    self.repository.update(
                        db,
                        existing.id,
                        {"price_per_stroke": price, **update_audit},
                        commit=False,
                    )
                    updated_count += 1
                else:
                    self.repository.create(
                        db,
                        {
                            "location": location,
                            "year": year,
                            "tonnage": row.tonnage,
                            "price_per_stroke": price,
                            **create_audit,
                        },
                        commit=False,
                    )
                    created_count += 1
            db.commit()
        except Exception:
            db.rollback()
            raise

        warnings = list(parse_result.errors)
        message = (
            f"导入完成：基地「{location}」{year} 年，"
            f"新增 {created_count} 条，更新 {updated_count} 条"
        )
        if warnings:
            message += f"；有 {len(warnings)} 行跳过"

        logger.info(
            "%s file=%s created=%s updated=%s warnings=%s",
            message,
            original_name,
            created_count,
            updated_count,
            len(warnings),
        )
        return StampingTonnagePriceImportResultVO(
            location=location,
            year=year,
            created_count=created_count,
            updated_count=updated_count,
            total_count=created_count + updated_count,
            skipped_count=len(warnings),
            warnings=warnings,
            message=message,
        )
