"""
钢材基准价格 Excel 解析器
解析 "发布价格及中标钢厂.xlsx" 格式：
- Sheet1: 主数据，定价表（宽表结构，列 = 基地，每个基地 2~3 列）
- Sheet2: 中标钢厂对照（材质 → 各基地钢厂）【暂未启用】
"""

import io
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import openpyxl
import xlrd


# ============================================================
# 第1层：数据类定义
# ============================================================

@dataclass
class BaseColumnConfig:
    """基地列配置"""
    location: str          # 基地名称（如 "芜湖"）
    mill_col: int          # 钢厂列索引（0-based）
    price_col: int         # 价格列索引（0-based）


@dataclass
class ParsedContext:
    """解析上下文"""
    year: Optional[int]
    month: Optional[int]
    base_configs: List[BaseColumnConfig]
    spec_col: int = 3  # 规格列索引（默认第4列，兼容旧格式）
    sheet_name: str = "Sheet1"


@dataclass
class ParseResult:
    """解析结果"""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    records: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.records)


# ============================================================
# 第2层：辅助函数（工具层）
# ============================================================

def _str(value: Any) -> str:
    """安全转换为去空白字符串，空值返回空字符串"""
    if value is None:
        return ""
    return str(value).strip()


def _decimal(value: Any) -> Optional[Decimal]:
    """
    安全转换为 Decimal
    支持：数字、字符串数字；失败或空值返回 None
    特殊值（-、/、#N/A、待商务发布等）返回 None
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except Exception:
            return None

    s = str(value).strip()
    if not s or s in ("-", "/", "#N/A", "#VALUE!", "None", "待商务发布"):
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


def _parse_year_month(text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    从文本中解析年月
    支持格式：2025年1月、2025-1、2025.1、202501
    返回 (year, month)，失败返回 (None, None)
    """
    text = _str(text)
    patterns = [
        r'(\d{4})[年\-\.](\d{1,2})',  # 2025年1月、2025-1、2025.1
        r'(\d{4})(\d{2})',             # 202501
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            if 2000 <= year <= 2100 and 1 <= month <= 12:
                return year, month
    return None, None


def _parse_spec(spec_str: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    解析规格字符串，支持格式：
    - 1.0*1250
    - .0*1250 → 自动修正为 1.0*1250（2024年表格常见笔误）
    - 0.7*1250
    返回 (厚度, 宽度)，解析失败返回 (None, None)
    """
    if not spec_str:
        return None, None

    # 匹配 厚度*宽度，厚度部分允许以 . 开头
    match = re.match(r'([\d.]*[\d]+)\*(\d+)', spec_str)
    if match:
        thick_str = match.group(1)

        # 业务修正：.0 → 1.0（Excel 中常省略前面的 1）
        if thick_str.startswith('.'):
            thick_str = '1' + thick_str

        thick = _decimal(thick_str)
        width = _decimal(match.group(2))
        return thick, width

    return None, None


def _parse_sheet2(wb: openpyxl.Workbook) -> Dict[str, Dict[str, str]]:
    """
    解析 Sheet2，返回映射：{ grade -> { location -> steel_mill } }
    列布局：A=材质, B=芜湖钢厂, C=大连钢厂, D=青岛钢厂
    【当前未启用，保留备用】
    """
    result: Dict[str, Dict[str, str]] = {}
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


# ============================================================
# 第3层：表头解析器（元数据提取）
# ============================================================

def _extract_year_month_from_sheet(ws) -> Tuple[Optional[int], Optional[int]]:
    """从工作表前3行提取年月"""
    for row in ws.iter_rows(min_row=1, max_row=3, values_only=True):
        for cell in row:
            if cell:
                ym = _parse_year_month(str(cell))
                if ym:
                    return ym
    return None, None


def _extract_base_configs(ws) -> List[BaseColumnConfig]:
    """
    从第4行(基地名)和第5行(子标题)动态识别所有基地列对。
    支持：
    - 2列/基地：钢厂 + 价格（紧挨着）
    - 3列/基地：钢厂 + 空列 + 价格（隔了一列）
    - 1列/基地：只有价格列（如"到厂原卷承兑价格"，无独立钢厂列）
    返回 BaseColumnConfig 列表。
    """
    header_row = list(ws.iter_rows(min_row=4, max_row=4, values_only=True))[0]
    sub_row = list(ws.iter_rows(min_row=5, max_row=5, values_only=True))[0]

    configs = []
    # 从第5列（索引4）开始扫描，前4列是固定列（序号、钢种、牌号、规格）
    for idx in range(4, len(header_row)):
        base_name = _str(header_row[idx])
        sub_text = _str(sub_row[idx]) if idx < len(sub_row) else ""

        if not base_name:
            continue

        # 判断是否为"钢厂"列（根据子标题）
        is_mill_col = sub_text and ("中标钢厂" in sub_text or "钢厂" in sub_text)
        if not is_mill_col:
            continue

        # 从当前位置向后扫描，找第一个"价格"列
        price_col = None
        for lookahead in range(idx + 1, len(header_row)):
            lookahead_sub = _str(sub_row[lookahead]) if lookahead < len(sub_row) else ""

            # 找到价格列
            if lookahead_sub and ("价格" in lookahead_sub or "承兑" in lookahead_sub):
                price_col = lookahead
                break

            # 如果遇到下一个基地名（非空且不是当前基地），说明当前基地缺少价格列，停止扫描
            next_base = _str(header_row[lookahead])
            if next_base and next_base != base_name:
                break

        if price_col is not None:
            location = base_name.replace("基地", "").strip()
            configs.append(BaseColumnConfig(
                location=location,
                mill_col=idx,
                price_col=price_col
            ))
        # 如果找不到价格列，跳过该基地（后续可在 warnings 中记录）

    # 备用逻辑：如果上面没有识别到任何基地，尝试直接识别价格列
    # 适用于 Row5 只有"到厂原卷承兑价格"等价格标注，没有"钢厂"字样的格式
    if not configs:
        for idx in range(4, len(header_row)):
            base_name = _str(header_row[idx])
            sub_text = _str(sub_row[idx]) if idx < len(sub_row) else ""

            if not base_name:
                continue

            # 检查是否包含价格关键词（说明这是价格列）
            if sub_text and ("价格" in sub_text or "承兑" in sub_text):
                location = base_name.replace("基地", "").strip()
                configs.append(BaseColumnConfig(
                    location=location,
                    mill_col=idx,  # 复用价格列作为 mill_col（实际数据为空时会跳过）
                    price_col=idx
                ))
            elif not sub_text and base_name not in ("合计", "厚度加减价", "未税合计", "含税合计"):
                # 无副标题的基地名列，尝试向后找价格列
                for lookahead in range(idx + 1, len(header_row)):
                    lookahead_sub = _str(sub_row[lookahead]) if lookahead < len(sub_row) else ""
                    if lookahead_sub and ("价格" in lookahead_sub or "承兑" in lookahead_sub):
                        location = base_name.replace("基地", "").strip()
                        configs.append(BaseColumnConfig(
                            location=location,
                            mill_col=idx,
                            price_col=lookahead
                        ))
                        break

    return configs

def _extract_processing_fee_col(ws) -> Optional[int]:
    """
    从第4行或第5行查找"加工费"列的索引（0-based）
    返回列索引，找不到返回 None
    """
    # 先查第4行（基地名行）
    header_row = list(ws.iter_rows(min_row=4, max_row=4, values_only=True))[0]
    for idx, cell in enumerate(header_row):
        if cell and "加工费" in str(cell):
            return idx

    # 再查第5行（子标题行）
    sub_row = list(ws.iter_rows(min_row=5, max_row=5, values_only=True))[0]
    for idx, cell in enumerate(sub_row):
        if cell and "加工费" in str(cell):
            return idx

    return None


def _find_spec_column(ws) -> Optional[int]:
    """
    从表头行（第4行或第5行）查找"参考规格"或"规格"列的索引。
    返回列索引（0-based），找不到返回 None。
    """
    # 检查第4行（索引3）和第5行（索引4）
    for row_idx in [4, 5]:
        try:
            header_row = list(ws.iter_rows(min_row=row_idx, max_row=row_idx, values_only=True))[0]
        except (IndexError, StopIteration):
            continue

        for col_idx, cell in enumerate(header_row):
            cell_str = _str(cell)
            if not cell_str:
                continue

            # 优先精确匹配"参考规格"
            if "参考规格" in cell_str:
                return col_idx
            # 兜底匹配"规格"（排除"规格型号"等过长词）
            if "规格" in cell_str and len(cell_str) <= 10:
                return col_idx

    return None


# ============================================================
# 第4层：行数据映射器
# ============================================================

def _map_row_to_records(
    row: tuple,
    context: ParsedContext,
    excel_row_num: int,
    processing_fee: Decimal
) -> List[Dict[str, Any]]:
    """
    将一行 Excel 数据 + 基地配置 → 多条数据库记录（每个基地一条）
    """
    records = []

    def safe_get(index: int, default: str = "") -> str:
        return _str(row[index]) if len(row) > index else default

    steel_type = safe_get(1)
    grade = safe_get(2).replace("//", "/")

    # 使用动态规格列索引
    spec_str = safe_get(context.spec_col)
    thick, width = _parse_spec(spec_str) if spec_str else (None, None)

    # 如果钢种或牌号为空，直接返回空列表
    if not steel_type or not grade:
        return []

    for cfg in context.base_configs:
        mill = safe_get(cfg.mill_col)
        price = _decimal(row[cfg.price_col]) if len(row) > cfg.price_col else None

        # 只有钢厂和价格都存在时才生成记录
        if mill and price is not None:
            records.append({
                "year": context.year,
                "month": context.month,
                "location": cfg.location,
                "steel_mill": mill,
                "category_name": steel_type,
                "grade": grade,
                "spec": spec_str,
                "thick": thick,
                "width": width,
                "base_price": price,
                "processing_fee": processing_fee,
                "excel_filename": "",
                "sheet_name": context.sheet_name,
                "excel_row": excel_row_num,
                "excel_col": cfg.price_col + 1,  # 转为 1-based 列号
                "remark": None,
            })

    return records

def _find_data_sheet(wb) -> Optional[Any]:
    """
    自动查找包含数据的工作表。
    识别规则：在第4行或第5行能找到"钢种"、"牌号"、"规格"等关键列名。
    返回 Worksheet 对象，找不到返回 None。
    """
    # 优先检查常见名称，
    # Sheet1 2025,2026都是这个表页。
    # 2024 4订5是 发布价汇总价 2024 5订6是汇总价格
    preferred_names = ["Sheet1", "发布价汇总价", "总价格", "汇总价格"]
    for name in preferred_names:
        if name in wb.sheetnames:
            ws = wb[name]
            # 简单验证：检查第4行或第5行是否有"钢种"
            try:
                row4 = list(ws.iter_rows(min_row=4, max_row=4, values_only=True))[0]
                row5 = list(ws.iter_rows(min_row=5, max_row=5, values_only=True))[0]
                header_text = " ".join([_str(cell) for cell in row4 + row5 if cell])
                if "钢种" in header_text or "牌号" in header_text:
                    return ws
            except (IndexError, StopIteration):
                continue
    
    # 遍历所有工作表，找到第一个包含关键列的工作表
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        
        for row_idx in [4, 5]:
            try:
                header_row = list(ws.iter_rows(min_row=row_idx, max_row=row_idx, values_only=True))[0]
                header_text = " ".join([_str(cell) for cell in header_row if cell])
                
                keywords = ["钢种", "牌号", "规格", "钢厂", "价格"]
                if any(kw in header_text for kw in keywords):
                    return ws
            except (IndexError, StopIteration):
                continue
    
    # 兜底：返回第一个非空工作表
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        try:
            first_data_row = list(ws.iter_rows(min_row=6, max_row=6, values_only=True))[0]
            if any(cell is not None and _str(cell) for cell in first_data_row[:5]):
                return ws
        except (IndexError, StopIteration):
            continue
    
    return None


# ============================================================
# 第4.5层：XLS 文件兼容层（xlrd）
# ============================================================

class _XlsSheetWrapper:
    """
    xlrd Worksheet → openpyxl Worksheet 接口适配层。
    将 xlrd 的行数据包装为类似 openpyxl 的形式，使上层解析逻辑无需改动。
    """

    def __init__(self, sheet: xlrd.sheet.Sheet):
        self._sheet = sheet

    @property
    def title(self) -> str:
        return self._sheet.name

    def iter_rows(self, min_row: int = 1, max_row: Optional[int] = None,
                  values_only: bool = True) -> List[List[Any]]:
        """
        模拟 openpyxl.iter_rows(..., values_only=True) 的行为。
        xlrd 行号从 0 开始；openpyxl 从 1 开始。
        参数 min_row/max_row 采用 openpyxl 的 1-based 语义。
        """
        results: List[List[Any]] = []
        row_count = self._sheet.nrows
        actual_min = max(0, min_row - 1)
        actual_max = row_count if max_row is None else min(max_row, row_count)

        for row_idx in range(actual_min, actual_max):
            row_values: List[Any] = []
            for col_idx in range(self._sheet.ncols):
                cell = self._sheet.cell(row_idx, col_idx)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    # 日期单元格转为 Python date/datetime
                    try:
                        date_tuple = xlrd.xldate_as_tuple(cell.value, self._sheet.book.datemode)
                        if date_tuple[3:] == (0, 0, 0):
                            row_values.append(date_tuple[:3])  # (year, month, day)
                        else:
                            row_values.append(date_tuple)
                    except Exception:
                        row_values.append(cell.value)
                elif cell.ctype == xlrd.XL_CELL_EMPTY:
                    row_values.append(None)
                elif cell.ctype == xlrd.XL_CELL_TEXT:
                    row_values.append(cell.value)
                elif cell.ctype == xlrd.XL_CELL_NUMBER:
                    # 整数转 int，浮点数保持 float
                    val = cell.value
                    if val == int(val):
                        row_values.append(int(val))
                    else:
                        row_values.append(val)
                elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                    row_values.append(bool(cell.value))
                elif cell.ctype == xlrd.XL_CELL_ERROR:
                    row_values.append(None)
                elif cell.ctype == xlrd.XL_CELL_BLANK:
                    row_values.append(None)
                else:
                    row_values.append(cell.value)
            results.append(row_values)
        return results


class _XlsWorkbookWrapper:
    """
    xlrd Workbook → openpyxl Workbook 接口适配层。
    提供 sheetnames 和 [] 访问器，供上层统一调用。
    """

    def __init__(self, book: xlrd.Book):
        self._book = book
        self._sheets: Dict[str, _XlsSheetWrapper] = {
            s.name: _XlsSheetWrapper(s) for s in book.sheets()
        }

    @property
    def sheetnames(self) -> List[str]:
        return list(self._sheets.keys())

    def __getitem__(self, name: str) -> _XlsSheetWrapper:
        if name not in self._sheets:
            raise KeyError(f"Sheet '{name}' not found in workbook")
        return self._sheets[name]


def _is_xls_file(file_content: bytes) -> bool:
    """根据文件魔数（Magic Number）判断是否为 XLS 格式。"""
    if len(file_content) < 4:
        return False
    # XLS 文件以复合文档头开始（OLE2 Format）
    return file_content[:4] == b'\xD0\xCF\x11\xE0'


# ============================================================
# 第5层：流程编排器（入口函数）
# ============================================================

def parse_base_price_excel(file_content: bytes) -> ParseResult:
    """
    入口函数：解析钢材基准价格 Excel 文件（支持 .xlsx 和 .xls），返回 ParseResult

    参数：
        file_content: Excel 文件的字节流（.xlsx 或 .xls 格式）

    返回：
        ParseResult: 包含 records、warnings、errors
    """
    result = ParseResult()

    # ---------- 1. 根据文件格式选择加载方式 ----------
    try:
        if _is_xls_file(file_content):
            # XLS 格式：使用 xlrd
            wb = xlrd.open_workbook(file_contents=file_content)
            wrapper = _XlsWorkbookWrapper(wb)
        else:
            # XLSX 格式：使用 openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
            wrapper = wb  # openpyxl.Workbook 本身支持 sheetnames 和 [] 访问
    except Exception as e:
        result.errors.append(f"无法打开 Excel 文件: {e}")
        return result

    # ---------- 2. 自动查找数据表 ----------
    # 统一接口：wrapper.sheetnames / wrapper[sheet_name]
    ws = _find_data_sheet(wrapper)
    if ws is None:
        result.errors.append("未找到包含有效数据的工作表（未找到钢种/牌号/规格等关键列）")
        return result
    # 记录实际使用的 sheet 名称（供后续参考）
    actual_sheet_name = ws.title
    # 如果 sheet 名称有变化，可以在 warnings 中记录
    if actual_sheet_name != "Sheet1":
        result.warnings.append(f"使用工作表: {actual_sheet_name}")

    # ---------- 2. 提取元数据（年月 + 基地配置） ----------
    year, month = _extract_year_month_from_sheet(ws)
    if not year:
        result.warnings.append("无法从 Excel 标题行提取年月，将使用接口传入的年度月份")

    base_configs = _extract_base_configs(ws)
    if not base_configs:
        result.errors.append("未能识别任何基地列，请检查表头格式")
        return result

    # 动态识别规格列
    spec_col = _find_spec_column(ws)
    if spec_col is None:
        spec_col = 3  # 默认第4列，兼容旧格式
        result.warnings.append("未找到规格列，使用默认列索引 3（第4列）")
    else:
        result.warnings.append(f"规格列位于第 {spec_col + 1} 列")

    context = ParsedContext(
        year=year,
        month=month,
        base_configs=base_configs,
        spec_col=spec_col,
        sheet_name=actual_sheet_name
    )

    # ---------- 3. 动态识别加工费列 ----------
    fee_col = _extract_processing_fee_col(ws)
    if fee_col is None:
        fee_col = 8  # 默认值，兼容旧格式
        result.warnings.append("未找到加工费列，使用默认列索引 8")

    # ---------- 4. 解析 Sheet2（保留备用，暂未启用） ----------
    # mill_map = _parse_sheet2(wb)
    # 如后续需要校验钢厂名，可传入 context

    # ---------- 5. 循环处理数据行（第6行开始） ----------
    skip_count = 0
    processed_rows = 0

    for row in ws.iter_rows(min_row=6, values_only=True):
        # 检查序号是否有效
        seq = row[0]
        if seq is None:
            continue
        try:
            int(seq)
        except (ValueError, TypeError):
            continue

        # 计算真实 Excel 行号
        excel_row_num = 6 + processed_rows

        # 获取加工费
        processing_fee = _decimal(row[fee_col]) or Decimal("120.00")

        # 调用行映射器
        records = _map_row_to_records(row, context, excel_row_num, processing_fee)

        if not records:
            skip_count += 1
        else:
            result.records.extend(records)

        processed_rows += 1

    if skip_count > 0:
        result.warnings.append(f"跳过 {skip_count} 行（钢种或牌号为空或无法解析）")

    # ---------- 6. 排序：按列升序（基地从左到右），再按行升序（原始行号） ----------
    result.records.sort(key=lambda r: (r.get('excel_col', 0), r.get('excel_row', 0)))

    return result