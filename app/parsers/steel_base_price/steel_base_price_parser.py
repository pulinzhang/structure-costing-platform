import io
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from decimal import Decimal

# ---------- 第1层：数据类定义（明确数据结构） ----------
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
    sheet_name: str = "Sheet1"

@dataclass
class ParseResult:
    """解析结果"""
    errors: List[str] = None
    warnings: List[str] = None
    records: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.records is None:
            self.records = []


# ---------- 第2层：元数据/表头解析器（专注找列） ----------
def _extract_year_month_from_sheet(ws: Worksheet) -> Tuple[Optional[int], Optional[int]]:
    """从工作表前3行提取年月"""
    for row in ws.iter_rows(min_row=1, max_row=3, values_only=True):
        for cell in row:
            if cell:
                ym = _parse_year_month(str(cell))  # 复用你原有的函数
                if ym:
                    return ym
    return None, None

def _extract_base_configs(ws: Worksheet) -> List[BaseColumnConfig]:
    """
    从第4行(基地名)和第5行(子标题)动态识别所有基地列对。
    返回 BaseColumnConfig 列表。
    """
    header_row = list(ws.iter_rows(min_row=4, max_row=4, values_only=True))[0]
    sub_row = list(ws.iter_rows(min_row=5, max_row=5, values_only=True))[0]
    
    configs = []
    # 从第5列（索引4）开始扫描，因为前4列是固定列（序号、钢种、牌号、规格）
    for idx in range(4, len(header_row)):
        base_name = _str(header_row[idx])
        sub_text = _str(sub_row[idx]) if idx < len(sub_row) else ""
        if not base_name:
            continue
            
        # 判断是否为“钢厂”列（根据子标题）
        if sub_text and ("中标钢厂" in sub_text or "钢厂" in sub_text):
            # 检查下一列是否为对应的“价格”列
            next_idx = idx + 1
            if next_idx < len(header_row):
                next_sub = _str(sub_row[next_idx]) if next_idx < len(sub_row) else ""
                if next_sub and ("价格" in next_sub or "承兑" in next_sub):
                    location = base_name.replace("基地", "").strip()
                    configs.append(BaseColumnConfig(
                        location=location,
                        mill_col=idx,
                        price_col=next_idx
                    ))
                else:
                    # 如果顺序不是“钢厂+价格”，可以在这里记录警告（但暂不阻断）
                    pass
    return configs


# ---------- 辅助函数 ----------

def _str(value: Any) -> str:
    """安全转换为字符串"""
    if value is None:
        return ""
    return str(value).strip()

def _decimal(value: Any) -> Optional[Decimal]:
    """安全转换为 Decimal"""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None

def _parse_spec(spec_str: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    解析规格字符串，如 "0.7*1250" → (0.7, 1250)
    返回 (厚度, 宽度)，解析失败返回 (None, None)
    """
    if not spec_str:
        return None, None
    # 匹配 数字*数字 格式
    match = re.match(r'([\d.]+)\*(\d+)', spec_str)
    if match:
        thick = _decimal(match.group(1))
        width = _decimal(match.group(2))
        return thick, width
    return None, None

def _parse_year_month(text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    从文本中解析年月，如 "2025年1月" → (2025, 1)
    支持格式：2025年1月、2025-1、2025.1 等
    """
    text = _str(text)
    # 匹配年月
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

def _parse_sheet2(wb) -> Dict[str, str]:
    """
    解析 Sheet2，返回中标钢厂映射（钢种 → 钢厂名）
    如果 Sheet2 不存在，返回空字典
    """
    if "Sheet2" not in wb.sheetnames:
        return {}
    
    ws2 = wb["Sheet2"]
    mill_map = {}
    
    # 假设格式：第1列钢种，第2列中标钢厂
    for row in ws2.iter_rows(min_row=1, values_only=True):
        if row[0] and row[1]:
            steel_type = _str(row[0])
            mill_name = _str(row[1])
            if steel_type:
                mill_map[steel_type] = mill_name
    
    return mill_map


# ---------- 第3层：行数据映射器（专注把一行变成多条记录） ----------
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
    steel_type = _str(row[1])
    grade = _str(row[2]).replace("//", "/")
    spec_str = _str(row[3])
    thick, width = _parse_spec(spec_str)  # 复用你原有的解析函数
    
    # 如果钢种或牌号为空，直接返回空列表（调用方负责统计跳过行数）
    if not steel_type or not grade:
        return []
    
    for cfg in context.base_configs:
        mill = _str(row[cfg.mill_col])
        price = _decimal(row[cfg.price_col])
        if mill and price is not None:
            records.append({
                "year": context.year,
                "month": context.month,
                "location": cfg.location,
                "steel_mill": mill,
                "category_name": steel_type,
                "grade": grade,
                "spec": spec_str,          # 新增：原始规格字符串
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


# ---------- 第4层：流程编排器（原入口函数，现在只做“组装”工作） ----------
def parse_base_price_excel(file_content: bytes) -> ParseResult:
    """
    入口函数：组装所有模块，返回 ParseResult
    """
    result = ParseResult()
    
    # 1. 加载文件（I/O 职责）
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
    except Exception as e:
        result.errors.append(f"无法打开 Excel 文件: {e}")
        return result
    
    if "Sheet1" not in wb.sheetnames:
        result.errors.append("未找到 Sheet1")
        return result
    ws = wb["Sheet1"]
    
    # 2. 提取元数据（年/月 + 基地配置）
    year, month = _extract_year_month_from_sheet(ws)
    if not year:
        result.warnings.append("无法从 Excel 标题行提取年月，将使用接口传入的年度月份")
    
    base_configs = _extract_base_configs(ws)
    if not base_configs:
        result.errors.append("未能识别任何基地列，请检查表头格式")
        return result
    
    context = ParsedContext(year=year, month=month, base_configs=base_configs)
    
    # 3. 解析 Sheet2（保留你原有的逻辑，这是独立的）
    mill_map = _parse_sheet2(wb)  # 如果你后续要用，可以传到上下文里
    
    # 4. 循环处理数据行（第6行开始）
    skip_count = 0
    for row_idx, row in enumerate(ws.iter_rows(min_row=6, values_only=True), start=6):
        seq = row[0]
        if seq is None:
            continue
        try:
            int(seq)
        except (ValueError, TypeError):
            continue
        
        # 获取加工费（固定列索引8，如果以后需要动态识别可再抽离）
        processing_fee = _decimal(row[8]) or Decimal("120.00")
        
        # 调用行映射器（excel_row 使用真实的行号）
        records = _map_row_to_records(row, context, row_idx, processing_fee)
        if not records:
            skip_count += 1
            continue
        
        result.records.extend(records)
    
    if skip_count > 0:
        result.warnings.append(f"跳过 {skip_count} 行（钢种或牌号为空或无法解析）")
    
    # ---------- 排序：按基地列升序，再按原始行号升序 ----------
    result.records.sort(key=lambda r: (r.get('excel_col', 0), r.get('excel_row', 0)))

    return result