"""单元格取值：身份列、利废/摆剪、成品费率公式。"""

from __future__ import annotations

from decimal import Decimal

from app.common.bom.manufacturing_category import short_part_number_digits
from app.common.swing_shear import steel_kg_price_with_swing_shear
from app.services.costing.stamping_part_cost.export.formatters import formula_number
from app.services.costing.stamping_part_cost.helpers import (
    format_number as _num,
)
from app.services.costing.stamping_part_cost.helpers import (
    to_decimal,
)


def _steel_kg_for_material(row: object) -> Decimal | None:
    """钢板单价(元/kg) = (联动吨价 + 本月摆剪加价) / 1000。"""
    steel_ton = to_decimal(getattr(row, "steel_ton_price", None))
    if steel_ton is None:
        return None
    surcharge = to_decimal(getattr(row, "swing_shear_fee_per_ton", None)) or Decimal("0")
    return steel_kg_price_with_swing_shear(steel_ton, surcharge)


def _swing_shear_fee_cell(row: object) -> Decimal | str:
    if not getattr(row, "has_swing_shear", False):
        return ""
    number = to_decimal(getattr(row, "swing_shear_fee_per_ton", None))
    if number is None:
        return ""
    return _num(number, 2)


def _part_identity_cells(
    row: object,
    *,
    seq: object,
    assembly_supply_no: str,
) -> dict[str, object]:
    return {
        "A": seq,
        "B": getattr(row, "stamping_supplier", None) or "",
        "C": getattr(row, "version", None) or "",
        "D": assembly_supply_no,
        "E": getattr(row, "part_number", None) or "",
        "F": short_part_number_digits(getattr(row, "part_number", None)) or "",
        "G": getattr(row, "part_name", None) or "",
        "H": "",
        "I": getattr(row, "material", None) or "",
    }


def _offal_and_swing_cells(row: object) -> dict[str, object]:
    return {
        "AP": "是" if getattr(row, "is_offal_nested", False) else "否",
        "AQ": getattr(row, "offal_source", None) or "",
        "AR": "是" if getattr(row, "has_swing_shear", False) else "否",
        "AS": _swing_shear_fee_cell(row),
    }


def _fee_amount_cell(value: object, digits: int) -> Decimal | str:
    """加工费 / 模具费 / 检具费：None 或 0 导出为空，不写 0。"""
    number = to_decimal(value)
    if number is None or number == 0:
        return ""
    return _num(number, digits)


def _finished_fee_formula_cells(
    excel_row: int,
    *,
    warehouse_packaging_rate: Decimal,
    management_rate: Decimal,
    finance_rate: Decimal,
    pretax_profit_rate: Decimal,
) -> dict[str, object]:
    """直接成本 + 四项费用（固定顺序）+ 最终价，均为 Excel 公式。

    顺序：仓储+包装 → 管理费 → 财务费 → 税前利润
    费率须为系统配置 Decimal（禁止用费用÷直接成本反推，会出脏小数）。
    直接成本为 0 时单元格显示空（与加工费/模具费/检具费一致）。
    """
    v = f"Y{excel_row}"
    direct = f"U{excel_row}+V{excel_row}+W{excel_row}+X{excel_row}"
    return {
        "Y": f'=IF(({direct})=0,"",{direct})',
        "Z": f'=IF({v}="","",{v}*{formula_number(warehouse_packaging_rate)})',
        "AA": f'=IF({v}="","",{v}*{formula_number(management_rate)})',
        "AB": f'=IF({v}="","",{v}*{formula_number(finance_rate)})',
        "AC": f'=IF({v}="","",{v}*{formula_number(pretax_profit_rate)})',
        "AD": (f'=IF({v}="","",{v}+Z{excel_row}+AA{excel_row}' f"+AB{excel_row}+AC{excel_row})"),
    }


def _part_size_formula(material_row: int, thickness_row: int) -> str:
    """零件尺寸 = 材质-料厚；整数料厚用 TEXT 保留 1 位小数。"""
    return f'=I{material_row}&"-"&TEXT(J{thickness_row},"0.0###")'
