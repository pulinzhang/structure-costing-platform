"""采购对象成本还原导出。列与查询表相同，只写工作簿。"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session

from app.common.money import Q4, excel_money_cell
from app.schemas.dto.cost_restore_procurement_object_dto import CostRestoreProcurementObjectQuery
from app.services.costing.cost_restore.procurement_object.rows import RestoreLine
from app.services.costing.cost_restore.procurement_object.service import (
    CostRestoreProcurementObjectService,
)

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("supplier_name", "供应商"),
    ("vehicle_model", "项目"),
    ("object_kind", "分类"),
    ("internal_number", "物料编码"),
    ("object_part_number", "对象零件号"),
    ("object_part_name", "对象名称"),
    ("vehicle_qty", "单车用量"),
    ("settlement_price", "结算价"),
    ("row_type", "行类型"),
    ("leaf_part_number", "叶子零件号"),
    ("priced_part_number", "取价零件号"),
    ("sheet_length", "长"),
    ("sheet_width", "宽"),
    ("thickness", "厚"),
    ("parts_per_sheet", "可制件数"),
    ("blank_weight_kg", "单件毛坯消耗定额"),
    ("material", "材质"),
    ("finished_weight_kg", "产品净重"),
    ("utilization_pct", "材料利用率"),
    ("scrap_weight_kg", "废料重量"),
    ("scrap_price_per_kg", "废料价格"),
    ("swing_shear_fee_per_ton", "摆剪"),
    ("steel_price_per_kg", "钢板单价"),
    ("material_amount_sheet", "原材料金额"),
    ("loss_scrap_deduction", "损耗废料扣除"),
    ("process_scrap_deduction", "边角废料扣除"),
    ("material_net", "原材料净成本"),
    ("automation", "冲压模式"),
    ("process_code", "冲压工序"),
    ("tonnage", "机台吨位"),
    ("stroke_fee", "单冲费用"),
    ("die_length", "模具长"),
    ("die_width", "模具宽"),
    ("die_height", "模具高"),
    ("hollow_factor", "掏空系数"),
    ("die_sets", "套数"),
    ("die_weight_t", "模具重量"),
    ("material_cost", "原材料成本"),
    ("process_cost", "费用总计"),
    ("material_plus_process", "原材料加加工费"),
    ("die_fee", "模具费"),
    ("gauge_fee", "检具费"),
    ("finance_fee", "财务费"),
    ("management_fee", "管理费"),
    ("warehouse_fee", "仓储包装费"),
    ("profit_fee", "税前利润"),
    ("direct_cost", "直接成本"),
    ("unit_cost", "零件标准成本"),
    ("line_amount", "行金额"),
    ("outsourced_amount", "外购费用合计"),
    ("weld_name", "焊接名称"),
    ("weld_qty", "焊接数量"),
    ("weld_unit_price", "焊接单价"),
    ("weld_amount", "焊接费用"),
    ("ecoat_amount", "电泳费用"),
    ("part_cost_id", "零件价id"),
    ("process_fee_id", "加工费id"),
    ("die_fee_id", "模具费id"),
    ("gauge_fee_id", "检具费id"),
    ("steel_price_id", "钢价id"),
    ("scrap_price_id", "废料价id"),
    ("welding_fee_id", "焊接费id"),
    ("source_filename", "来源文件"),
    ("source_row", "来源行号"),
    ("calc_status", "核算状态"),
    ("remark", "备注"),
)

_SHEET_NAME = "采购对象"


def export_filename(location: str, year: int, month: int, vehicle_model: str | None) -> str:
    project = f"-{vehicle_model}" if vehicle_model else ""
    return f"成本还原-采购对象-{location}{project}-{year}年{month}月.xlsx"


class CostRestoreProcurementObjectExport:
    def __init__(self, service: CostRestoreProcurementObjectService | None = None) -> None:
        self._service = service or CostRestoreProcurementObjectService()

    def export(
        self,
        db: Session,
        query: CostRestoreProcurementObjectQuery,
    ) -> tuple[bytes, str]:
        lines, scope = self._service.lines_for_export(db, query)
        content = write_workbook(lines, qa_note=scope.qa_note)
        filename = export_filename(query.location, query.year, query.month, query.vehicle_model)
        return content, filename


def write_workbook(lines: list[RestoreLine], *, qa_note: str | None) -> bytes:
    book = Workbook()
    active = book.active
    if not isinstance(active, Worksheet):
        raise RuntimeError("导出工作簿没有工作表")
    sheet = active
    sheet.title = _SHEET_NAME
    header_row = 1
    if qa_note:
        sheet.cell(1, 1, qa_note).font = Font(bold=True)
        header_row = 2
    for index, (_field, title) in enumerate(_COLUMNS, start=1):
        cell = sheet.cell(header_row, index, title)
        cell.font = Font(bold=True)
        sheet.column_dimensions[get_column_letter(index)].width = max(len(title) + 2, 12)
    for row_index, line in enumerate(lines, start=header_row + 1):
        for column, (field, _title) in enumerate(_COLUMNS, start=1):
            sheet.cell(row_index, column, _cell_value(getattr(line, field)))
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _cell_value(value: object) -> Decimal | str | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        cell = excel_money_cell(value, Q4)
        return cell if isinstance(cell, Decimal) else None
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return str(value)
