"""BOM 年度零件价 Excel 导入 / 模板下载服务。"""

from __future__ import annotations

import logging
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.bom.annual_part_price_parser import parse_annual_part_price_excel
from app.repositories.bom.annual_part_price_repository import (
    BomAnnualPartPriceRepository,
)
from app.schemas.dto.bom_annual_part_price_dto import (
    BomAnnualPartPriceCreate,
    BomAnnualPartPriceUpdate,
    quantize_unit_price,
)
from app.schemas.vo.bom_annual_part_price_vo import BomAnnualPartPriceImportResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.utils.bom_annual_part_price_archive import save_annual_part_price_upload

logger = logging.getLogger("service.bom_annual_part_price_import")

# 零件号, 零件名称, 单位, 单价, 原供货类型, 供应商, 备注
# 样例来自生产外购价表（基地/年度由上传表单指定，不写进 Excel）
TEMPLATE_SAMPLE_ROWS: list[tuple[str, str, str, Decimal, str, str, str]] = [
    ("501004437AA", "中通道后纵梁本体II", "pcs", Decimal("2.1300"), "沿用", "", ""),
    ("501007904AA", "前排气管吊钩", "pcs", Decimal("4.0000"), "沿用", "", ""),
    ("501007905AA", "前纵梁排气管吊钩支架", "pcs", Decimal("1.7300"), "沿用", "", ""),
    ("QR36410", "焊接方螺母", "pcs", Decimal("0.1750"), "标准件", "", ""),
    ("501005123AA", "流水槽上加强梁本体", "pcs", Decimal("17.0400"), "沿用", "", ""),
    ("N0111931", "焊接方螺母", "pcs", Decimal("0.0420"), "标准件", "", ""),
    ("J60-5400253", "螺母盒", "pcs", Decimal("0.5000"), "沿用", "", ""),
    ("M11-5400251", "螺母板", "pcs", Decimal("2.0000"), "沿用", "", ""),
    ("J26-5600013", "后保上固定支架", "pcs", Decimal("1.0000"), "沿用", "", ""),
    ("Q1980616", "承面凸焊螺栓", "pcs", Decimal("0.0500"), "标准件", "", ""),
    ("504000341AA", "左D柱下结构增强胶块", "pcs", Decimal("31.4900"), "胶块", "", ""),
    ("504000342AA", "右D柱下结构增强胶块", "pcs", Decimal("31.4900"), "胶块", "", ""),
    ("501003649AA", "后防撞梁左安装板", "pcs", Decimal("2.8600"), "沿用", "", ""),
    ("501003650AA", "后防撞梁右安装板", "pcs", Decimal("2.7300"), "沿用", "", ""),
    ("501003646AA", "后防撞梁本体", "pcs", Decimal("22.1400"), "沿用", "", ""),
    ("501003651AA", "后拖车钩螺母加强板", "pcs", Decimal("2.5000"), "沿用", "", ""),
    ("501000701AA", "拖车钩螺母", "pcs", Decimal("5.0000"), "沿用", "", ""),
    ("N0111941", "焊接方螺母", "pcs", Decimal("0.1000"), "标准件", "", ""),
    ("T19C-6101521", "支撑柱", "pcs", Decimal("1.5000"), "标准件", "", ""),
    ("FQ114D0612T21F19E", "弧焊焊接螺柱与盖形螺母组合件", "pcs", Decimal("0.5290"), "标准件", "", ""),
    ("502003169AA", "左后门锁扣加强板", "pcs", Decimal("5.3800"), "沿用", "", ""),
    ("502002729AA", "螺母板总成", "pcs", Decimal("2.0000"), "沿用", "", ""),
    ("J60-5101162", "安全带加强板", "pcs", Decimal("3.0000"), "沿用", "", ""),
    ("QR366716", "凸焊螺母", "pcs", Decimal("0.4000"), "标准件", "", ""),
    ("Q1980620", "承面凸焊螺栓 M6X20", "pcs", Decimal("0.0620"), "标准件", "", ""),
    ("504000332AA", "C柱下内腔隔音胶块", "pcs", Decimal("0.8400"), "胶块", "", ""),
    ("504000339AA", "左D柱上结构增强胶块", "pcs", Decimal("19.3600"), "胶块", "", ""),
    ("504000340AA", "右D柱上结构增强胶块", "pcs", Decimal("19.3600"), "胶块", "", ""),
    ("TBD", "右D柱上结构增强胶块", "pcs", Decimal("19.3600"), "胶块", "", ""),
    ("502003968AA", "左前安全带滑轨上固定板总成", "pcs", Decimal("6.8800"), "沿用", "", ""),
    ("502002095AA", "乘客扶手安装支架I", "pcs", Decimal("1.9400"), "沿用", "", ""),
    ("502003562AA", "前安全带上安装板Ⅰ", "pcs", Decimal("5.7400"), "沿用", "", ""),
    ("T15-5400791", "左前卷收器安装板", "pcs", Decimal("0.0000"), "沿用", "", ""),
    ("QR37108", "焊接方螺母", "pcs", Decimal("0.2100"), "标准件", "", ""),
    ("T15-5400792", "右前卷收器安装板", "pcs", Decimal("0.0000"), "沿用", "", ""),
    ("501003196AA", "后地板横梁Ⅱ本体", "pcs", Decimal("14.9100"), "沿用", "", ""),
    ("501003348AA", "第三排座椅中间安装加强板", "pcs", Decimal("5.7200"), "沿用", "", ""),
    ("501003289AA", "后地板横梁本体", "pcs", Decimal("14.6800"), "沿用", "", ""),
    ("501005159AA", "第二排座椅中间安装加强板", "pcs", Decimal("7.6700"), "沿用", "", ""),
    ("501009677AA", "第二排座椅中间安装加强板I", "pcs", Decimal("9.5200"), "沿用", "", ""),
    ("501009678AA", "第二排座椅中间安装加强板II", "pcs", Decimal("9.5200"), "沿用", "", ""),
    ("501004439AA", "油箱后安装支架", "pcs", Decimal("4.7300"), "沿用", "", ""),
    ("T11-5100233", "焊接六角凸缘螺母M10X1.25", "pcs", Decimal("0.3400"), "标准件", "", ""),
    ("QR36708", "凸焊螺母座", "pcs", Decimal("0.3500"), "标准件", "", ""),
    ("M14-4102311", "结构胶", "pcs", Decimal("0.0000"), "胶块", "", ""),
]


class BomAnnualPartPriceImportService:
    """年度零件价同步导入（不走异步任务）。"""

    def __init__(self) -> None:
        self.repository = BomAnnualPartPriceRepository()

    def build_template(self) -> tuple[bytes, str]:
        """生成导入模板。"""
        workbook = Workbook()
        sheet = workbook.worksheets[0]
        sheet.title = "年度零件价"

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

        headers = [
            "零件号",
            "零件名称",
            "单位",
            "单价",
            "原供货类型",
            "供应商",
            "备注",
        ]
        for col, title in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=col, value=title)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        for row_idx, sample in enumerate(TEMPLATE_SAMPLE_ROWS, start=2):
            values: list[str | Decimal] = list(sample)
            for col, value in enumerate(values, start=1):
                cell = sheet.cell(row=row_idx, column=col, value=value)
                cell.font = data_font
                cell.border = thin_border
                if col == 4:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    cell.number_format = "0.0000"
                elif col in (3, 5):
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

        widths = [18, 24, 8, 12, 12, 16, 20]
        for idx, width in enumerate(widths, start=1):
            sheet.column_dimensions[chr(64 + idx)].width = width
        sheet.freeze_panes = "A2"

        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue(), "年度零件价导入模板.xlsx"

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        location: str,
        year: int,
        current_user: UserVO,
    ) -> BomAnnualPartPriceImportResultVO:
        location = (location or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        if year < 2000 or year > 2100:
            raise BusinessException("年度不正确")

        original_name = Path(filename or "").name
        if Path(original_name).suffix.lower() != ".xlsx":
            raise BusinessException("仅支持 .xlsx 文件")
        if not file_content:
            raise BusinessException("文件内容为空")
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            raise BusinessException(f"文件过大，最大支持 {max_mb}MB")

        archive_path = save_annual_part_price_upload(
            file_content=file_content,
            filename=original_name,
            year=year,
            location=location,
        )
        archived_rel = to_upload_relpath(archive_path)

        parse_result = parse_annual_part_price_excel(file_content)
        if parse_result.errors and not parse_result.rows:
            raise BusinessException("；".join(parse_result.errors))
        if not parse_result.rows:
            raise BusinessException("未解析到有效数据行")

        created_count = 0
        updated_count = 0
        skipped_approved = 0
        create_audit = audit_create(current_user)
        update_audit = audit_update(current_user)

        try:
            for row in parse_result.rows:
                unit_price = quantize_unit_price(row.unit_price)
                existing = self.repository.get_by_location_year_part_number(
                    db, location, year, row.part_number
                )
                if existing:
                    if existing.audit_status == "approved":
                        skipped_approved += 1
                        continue
                    self.repository.update(
                        db,
                        existing.id,
                        BomAnnualPartPriceUpdate(
                            part_name=row.part_name,
                            unit=row.unit,
                            unit_price=unit_price,
                            supply_type=row.supply_type,
                            supplier_name=row.supplier_name,
                            remark=row.remark,
                        ),
                        updated_by=update_audit["updated_by"],
                    )
                    updated_count += 1
                else:
                    self.repository.create(
                        db,
                        BomAnnualPartPriceCreate(
                            location=location,
                            year=year,
                            part_number=row.part_number,
                            part_name=row.part_name,
                            unit=row.unit,
                            unit_price=unit_price,
                            supply_type=row.supply_type,
                            supplier_name=row.supplier_name,
                            remark=row.remark,
                        ),
                        created_by=create_audit["created_by"],
                        updated_by=create_audit["updated_by"],
                    )
                    created_count += 1
            register_existing(
                db,
                file_category="bom_annual_part_price",
                stored_relpath=archived_rel,
                original_filename=original_name,
                current_user=current_user,
                location=location,
                year=year,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        warnings = list(parse_result.errors)
        if skipped_approved:
            warnings.append(f"跳过已审核 {skipped_approved} 条（未覆盖）")
        message = (
            f"导入完成：基地「{location}」{year} 年，"
            f"新增 {created_count} 条，更新 {updated_count} 条"
        )
        if skipped_approved:
            message += f"，跳过已审核 {skipped_approved} 条"
        if parse_result.errors:
            message += f"；有 {len(parse_result.errors)} 行解析跳过"

        logger.info(
            "%s file=%s archived=%s created=%s updated=%s skipped_approved=%s warnings=%s",
            message,
            original_name,
            archived_rel,
            created_count,
            updated_count,
            skipped_approved,
            len(warnings),
        )
        return BomAnnualPartPriceImportResultVO(
            location=location,
            year=year,
            created_count=created_count,
            updated_count=updated_count,
            total_count=created_count + updated_count,
            skipped_count=len(parse_result.errors) + skipped_approved,
            warnings=warnings,
            message=message,
        )
