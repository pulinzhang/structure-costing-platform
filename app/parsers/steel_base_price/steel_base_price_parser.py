"""
钢材基准价格 Excel 解析器
解析 "发布价格及中标钢厂.xlsx" 格式：
- Sheet1: 主数据，定价表（宽表结构，列 = 基地，列 = 价格）
- Sheet2: 中标钢厂对照（材质 → 各基地钢厂）
"""

import io
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import openpyxl


@dataclass
class ParseResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.records)


def _decimal(v: Any) -> Decimal | None:
    """将数字或字符串转为 Decimal，失败或空值返回 None"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        try:
            return Decimal(str(v))
        except (InvalidOperation, ValueError):
            return None
    s = str(v).strip()
    if not s or s in ("-", "/", "#N/A", "#VALUE!", "None"):
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _str(v: Any) -> str | None:
    """转为去空白字符串，空时返回 None"""
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _parse_year_month(title: str) -> tuple[int, int] | None:
    """
    从 Excel 标题行提取年月。
    支持格式：
      - "外协钢板2026年5月订单(2026年6月原料)一事一议价格"
      - "外协钢板2025年12月订单(2026年1月原料)一事一议价格"
    返回 (year, month) 或 None
    """
    m = re.search(r"(\d{4})年(\d{1,2})月", title)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _parse_spec(spec_str: str | None) -> tuple[Decimal | None, Decimal | None]:
    """
    解析参考规格，如 "1.0*1250" → (thick=1.0, width=1250.0)
    """
    if not spec_str:
        return None, None
    m = re.match(r"([\d.]+)\s*\*\s*([\d.]+)", str(spec_str).strip())
    if m:
        thick = _decimal(m.group(1))
        width = _decimal(m.group(2))
        return thick, width
    return None, None


def _parse_sheet2(wb: openpyxl.Workbook) -> dict[str, dict[str, str]]:
    """
    解析 Sheet2，返回映射：{ grade -> { location -> steel_mill } }
    列布局：A=材质, B=芜湖钢厂, C=大连钢厂, D=青岛钢厂
    """
    result: dict[str, dict[str, str]] = {}
    if "Sheet2" not in wb.sheetnames:
        return result
    ws = wb["Sheet2"]
    location_cols = {"芜湖": 1, "大连": 2, "青岛": 3}
    for row in ws.iter_rows(min_row=3, values_only=True):
        if not row or len(row) < 2:
            continue
        grade = _str(row[0])
        if not grade:
            continue
        result[grade] = {}
        for loc, col_idx in location_cols.items():
            if col_idx >= len(row):
                continue
            mill = _str(row[col_idx])
            if mill and mill not in ("-", "/", "#N/A"):
                result[grade][loc] = mill
    return result


def parse_base_price_excel(file_content: bytes) -> ParseResult:
    """
    解析 "发布价格及中标钢厂.xlsx" 格式 Excel。

    Sheet1 布局：
      Row4: 序号 | 钢种 | 牌号 | 参考规格 | 芜湖 | 芜湖 | 青岛基地 | 青岛基地 | 加工费
      Row5: (空) | (空) | (空) | (空)     | 中标钢厂 | 到厂原卷承兑价格 | 中标钢厂 | 到厂原卷承兑价格 | (空)
      Row6+: 数据行（序号为数字的才处理）

    列索引（0-based）：
      0=序号, 1=钢种, 2=牌号, 3=参考规格,
      4=芜湖中标钢厂, 5=芜湖价格,
      6=青岛中标钢厂, 7=青岛价格,
      8=加工费
    """
    result = ParseResult()

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
    except Exception as e:
        result.errors.append(f"无法打开 Excel 文件: {e}")
        return result

    # 解析 Sheet2 中标钢厂对照
    mill_map = _parse_sheet2(wb)

    if "Sheet1" not in wb.sheetnames:
        result.errors.append("未找到 Sheet1")
        return result

    ws = wb["Sheet1"]

    # 提取标题行中的年月
    year_month: tuple[int, int] | None = None
    for row in ws.iter_rows(min_row=1, max_row=3, values_only=True):
        for cell in row:
            if cell:
                ym = _parse_year_month(str(cell))
                if ym:
                    year_month = ym
                    break
        if year_month:
            break

    if not year_month:
        # 无法从 Excel 标题提取年月，但 service 层会传入 year/month，这里只记录 warning
        result.warnings.append("无法从 Excel 标题行提取年月，将使用接口传入的年度月份")

    year, month = year_month if year_month else (None, None)
    processed_rows = 0
    skip_count = 0

    for row in ws.iter_rows(min_row=6, values_only=True):
        seq = row[0]
        if seq is None:
            continue
        try:
            int(seq)
        except (ValueError, TypeError):
            continue

        steel_type = _str(row[1])
        grade = _str(row[2])
        spec_str = _str(row[3])
        thick, width = _parse_spec(spec_str)
        processing_fee = _decimal(row[8]) or Decimal("120.00")

        if not steel_type or not grade:
            skip_count += 1
            continue

        sheet_name = "Sheet1"

        # 计算实际 Excel 行号（从第6行开始）
        actual_excel_row = processed_rows + 6

        # 芜湖基地（列4=价格, 列5=中标钢厂）→ 价格在 Excel 第5列(E)
        wuhu_price = _decimal(row[4])
        wuhu_mill = _str(row[5])
        if wuhu_mill and wuhu_price is not None:
            result.records.append({
                "year": year,
                "month": month,
                "location": "芜湖",
                "steel_mill": wuhu_mill,
                "category_name": steel_type,
                "grade": grade,
                "thick": thick,
                "width": width,
                "base_price": wuhu_price,
                "processing_fee": processing_fee,
                "excel_filename": "",
                "sheet_name": sheet_name,
                "excel_row": actual_excel_row,
                "excel_col": 5,  # 价格在 Excel 第5列(E)
                "remark": None,
            })

        # 青岛基地（列6=价格, 列7=中标钢厂）→ 价格在 Excel 第7列(G)
        qingdao_price = _decimal(row[6])
        qingdao_mill = _str(row[7])
        if qingdao_mill and qingdao_price is not None:
            result.records.append({
                "year": year,
                "month": month,
                "location": "青岛",
                "steel_mill": qingdao_mill,
                "category_name": steel_type,
                "grade": grade,
                "thick": thick,
                "width": width,
                "base_price": qingdao_price,
                "processing_fee": processing_fee,
                "excel_filename": "",
                "sheet_name": sheet_name,
                "excel_row": actual_excel_row,
                "excel_col": 7,  # 价格在 Excel 第7列(G)
                "remark": None,
            })

        processed_rows += 1

    if skip_count > 0:
        result.warnings.append(f"跳过 {skip_count} 行（钢种或牌号为空）")

    return result