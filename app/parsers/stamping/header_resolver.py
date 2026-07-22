"""
表头解析模块

负责：
- 识别数据 Sheet
- 定位表头行
- 构建 Header Context（一级/二级标题合并，支持隐式横向跨列填充）
- 建立列映射
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import openpyxl

from app.utils.logging_config import get_logger
from app.parsers.stamping.models.header import HeaderContext


logger = get_logger("parser.stamping.header")


# Header 路径匹配模式（精确匹配）
# 键名与数据库字段一一对应，值列表按优先级排序
COLUMN_PATTERNS: Dict[str, List[Tuple[str, int]]] = {
    "seq": [
        ("序号", 1000), ("No.", 900), ("S/N", 850),
    ],
    "part_no": [
        ("零件号", 1000), ("零件编号", 990), ("件号", 950),
        ("Part No.", 900), ("P/N", 850),
    ],
    "part_name": [
        ("零件名称", 1000), ("零件名", 950), ("名称", 900),
    ],
    "material": [
        ("材质", 1000), ("材料", 950), ("牌号", 900),
    ],
    "thickness": [
        ("料厚", 1000), ("板厚", 950), ("厚度", 900),
    ],
    "weight": [
        ("单重", 1000), ("零件重量", 950), ("重量", 900),
    ],
    "length": [
        ("料片长", 1000), ("长/宽下料", 1050), ("长", 700),
    ],
    "width": [
        ("料片宽", 1000), ("宽/下料冲孔", 1050), ("宽", 700),
    ],
    "count": [
        ("可制件数", 1000), ("件数", 950),
    ],
    "sheet_type": [
        ("料片式样", 1000), ("式样", 800),
    ],
    # 工艺		
    # 工序名称	工序	套数

    # 工序号 - 精确匹配 Excel 表头文本
    "op": [
        ("工序名称", 1000), ("OP", 900), ("Process", 800),
    ],
    # 工艺代码 - 精确匹配 Excel 表头文本
    "code": [
        ("工序", 1000), ("代号", 900),
    ],
    
    "die_set": [
        ("套数", 1000),
    ],
    "tonnage": [
        ("吨位", 1000), ("使用冲压设备吨位", 900),
    ],
    "die_type": [
        ("模具类型", 1000),
    ],
    "method": [
        ("成形方法", 1000), ("成形", 900), ("工艺方法", 800),
    ],
    "auto": [
        ("自动化", 1000),
    ],
    "remark": [
        ("备注", 1000), ("备注栏", 950),
    ],
}


class HeaderResolver:
    """表头解析器"""

    def __init__(self, get_value_fn):
        self._get_value = get_value_fn
        self.header_row: int = 0
        self.data_start_row: int = 0
        self.header_paths: Dict[str, str] = {} 
        self.col_map: Dict[str, int] = {} 

    def find_stamping_sheet(self, workbook) -> Optional[openpyxl.worksheet.worksheet.Worksheet]:
        """识别冲压数据Sheet"""
        for sheet in workbook.worksheets:
            for row_idx in range(1, min(16, sheet.max_row + 1)):
                row_values = [self._get_value(row_idx, col) for col in range(1, 25)]
                row_text = " ".join([str(v) for v in row_values if v])

                has_part = any(p in row_text for p in ["零件号", "件号", "Part No"])
                has_op = any(p in row_text for p in ["工序", "OP", "Process"])

                if has_part and has_op:
                    logger.info(f"找到数据Sheet: {sheet.title}, 行{row_idx}")
                    return sheet

        return workbook.active

    def find_header_row(self, sheet) -> int:
        """找到表头起始行"""
        for row_idx in range(1, 20):
            for col in range(1, min(30, sheet.max_column + 1)):
                text = self._get_value(row_idx, col)
                if text and ("零件号" in str(text) or "零件编号" in str(text)):
                    logger.info(f"找到表头行: {row_idx}")
                    return row_idx
        return 4

    def build_header_context(self, sheet, header_row: int) -> None:
        """
        构建 Header Context：支持合并单元格、隐式向右扩散填充及换行符清洗
        """
        header_paths: Dict[int, str] = {}
        max_col = min(35, sheet.max_column + 1)

        def clean_val(val: Any) -> str:
            if not val:
                return ""
            # 清洗换行符、回车以及前后空白，避免匹配失效
            return str(val).replace("\n", "").replace("\r", "").strip()

        # 第一步：识别一级标题
        primary_headers: Dict[int, str] = {}

        # 1. 扫描标准合并单元格
        for merged_range in sheet.merged_cells.ranges:
            if merged_range.min_row <= header_row <= merged_range.max_row:
                min_c = merged_range.min_col
                max_c = merged_range.max_col
                value = clean_val(self._get_value(header_row, min_c))
                if value:
                    for c in range(min_c, max_c + 1):
                        primary_headers[c] = value

        # 2. 扫描普通单格一级标题
        for col in range(1, max_col):
            if col not in primary_headers:
                value = clean_val(self._get_value(header_row, col))
                if value:
                    primary_headers[col] = value

        # 3. 【核心增强】向前/向右扩散填充（Forward Fill）
        # 解决类似截图右侧“工艺”大类下有多列子项但未显式做合并单元格的问题
        last_primary = ""
        for col in range(1, max_col):
            if col in primary_headers and primary_headers[col]:
                last_primary = primary_headers[col]
            elif last_primary and not primary_headers.get(col):
                # 只有当该列下方存在二级标题时，才自动继承左侧的一级大标题
                sub_val = clean_val(self._get_value(header_row + 1, col))
                if sub_val:
                    primary_headers[col] = last_primary

        logger.info(f"处理后的一级标题: {primary_headers}")

        # 第二步：扫描二级标题（位于表头行的下一行）
        sub_row = header_row + 1
        secondary_headers: Dict[int, str] = {}

        for col in range(1, max_col):
            value = clean_val(self._get_value(sub_row, col))
            if value:
                secondary_headers[col] = value

        logger.info(f"扫描到的二级标题: {secondary_headers}")

        # 第三步：合并成完整路径
        for col in range(1, max_col):
            if col in secondary_headers:
                primary = primary_headers.get(col, "")
                secondary = secondary_headers[col]
                # 如果一级和二级标题文本一样（如单行表头），则直接用二级名称
                if primary and primary != secondary:
                    path = f"{primary}/{secondary}"
                else:
                    path = secondary
                header_paths[col] = path
            elif col in primary_headers:
                header_paths[col] = primary_headers[col]

        self.header_paths = {str(k): v for k, v in header_paths.items()}
        logger.info(f"最终 Header 路径映射: {self.header_paths}")

    def build_col_map(self) -> Dict[str, int]:
        """
        根据 Header 路径建立列映射

        匹配规则：
        1. header_paths 存储的是 "一级/二级" 路径
        2. 精确匹配路径末尾文本（如 "工序"、"工序名称"、"吨位"）
        3. 优先使用高优先级（score 高）的匹配
        """
        col_map: Dict[str, int] = {}
        used_cols: set = set()
        all_matches: List[Tuple[int, str, int, str]] = []

        for col_str, path in self.header_paths.items():
            col = int(col_str)
            for col_name, patterns in COLUMN_PATTERNS.items():
                for pattern, score in patterns:
                    # 精确匹配路径末尾文本
                    # path 格式可能是 "工序/工序名称" 或 "吨位"
                    if path.endswith(pattern):
                        all_matches.append((score, col_name, col, pattern))
                        break

        # 按 score 从高到低排序
        all_matches.sort(key=lambda x: -x[0])

        # 依次选择：只选未被使用的列
        for score, col_name, col, pattern in all_matches:
            if col_name not in col_map and col not in used_cols:
                col_map[col_name] = col
                used_cols.add(col)

        self.col_map = col_map
        logger.info(f"生成的字段列映射 (col_map): {self.col_map}")
        return col_map

    def resolve(self, sheet) -> HeaderContext:
        """
        执行完整的表头解析流程。
        """
        self.header_row = self.find_header_row(sheet)
        self.data_start_row = self.header_row + 2
        self.build_header_context(sheet, self.header_row)
        self.build_col_map()

        return HeaderContext(
            header_row=self.header_row,
            data_start_row=self.data_start_row,
            col_map=self.col_map,
            header_paths=self.header_paths,
        )