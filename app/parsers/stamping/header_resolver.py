"""
表头解析模块

负责：
- 识别数据 Sheet
- 定位表头行
- 构建 Header Context（一级/二级标题合并）
- 建立列映射
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import openpyxl

from app.utils.logging_config import get_logger
from app.parsers.stamping.models.header import HeaderContext


logger = get_logger("parser.stamping.header")


# Header 路径匹配模式
# 格式: "一级/二级" 或 "字段名"
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
        ("料片长", 1000), ("长/", 1050), ("长", 700),
    ],
    "width": [
        ("料片宽", 1000), ("宽/", 1050), ("宽", 700),
    ],
    "count": [
        ("可制件数", 1000), ("件数", 950),
    ],
    "sheet_type": [
        ("料片式样", 1000), ("式样", 800),
    ],
    # 工序号（强约束字段）
    "op": [
        ("工艺/工序号", 2000), ("工艺/工序", 1900), ("工序号", 1800),
        ("工序", 1000), ("OP", 900), ("Process", 800),
    ],
    # 工艺代码（强约束字段）
    "code": [
        ("工艺/代号", 2000), ("工艺/工艺代码", 1950), ("工艺/工艺名称", 1900),
        ("工艺/工艺内容", 1850), ("代号", 1000), ("工艺代码", 1000),
    ],
    "die_set": [
        ("设备/套数", 2000), ("设备/模具套数", 1950), ("套数", 1000),
    ],
    "tonnage": [
        ("设备/吨位", 2000), ("设备/设备吨位", 1950), ("吨位", 1000),
    ],
    "die_type": [
        ("模具/类型", 2000), ("模具/模具类型", 1950), ("模具类型", 1000),
    ],
    "method": [
        ("模具/成形", 2000), ("模具/成形方法", 1950), ("成形", 1000),
    ],
    "auto": [
        ("模具/自动化", 2000), ("自动化", 1000),
    ],
    "remark": [
        ("备注", 1000), ("备注栏", 950),
    ],
}


class HeaderResolver:
    """表头解析器"""

    def __init__(self, get_value_fn):
        """
        Args:
            get_value_fn: 单元格值获取函数 (row, col) -> Any
        """
        self._get_value = get_value_fn
        self.header_row: int = 0
        self.data_start_row: int = 0
        self.header_paths: Dict[str, str] = {}  # col(str) -> "一级/二级"
        self.col_map: Dict[str, int] = {}  # 字段名 -> 列号

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
        构建 Header Context：将一级标题与二级标题合并成完整路径

        例如：
        Row 4 (一级): 工艺 | 使用冲压设备吨位 | 模具
        Row 5 (二级): 工序号 | 代号 | 套数 | 吨位 | 类型 | 成形方法 | 自动化

        结果：
        Col 12 -> "工艺/工序号"
        Col 13 -> "工艺/代号"
        Col 15 -> "设备/吨位"
        Col 16 -> "模具/类型"
        """
        header_paths: Dict[int, str] = {}

        # 第一步：识别一级标题（合并单元格）
        primary_headers: Dict[int, str] = {}  # col -> 一级标题

        for merged_range in sheet.merged_cells.ranges:
            if merged_range.min_row == header_row:
                # 这是一级标题行
                min_c = merged_range.min_col
                max_c = merged_range.max_col
                value = self._get_value(header_row, min_c)
                if value:
                    # 这个合并区域下的所有列都归属于这个一级标题
                    for c in range(min_c, max_c + 1):
                        primary_headers[c] = str(value).strip()

        # 也检查非合并的一级标题
        for col in range(1, min(30, sheet.max_column + 1)):
            if col not in primary_headers:
                value = self._get_value(header_row, col)
                if value:
                    primary_headers[col] = str(value).strip()

        logger.info(f"一级标题: {primary_headers}")

        # 第二步：扫描二级标题
        sub_row = header_row + 1
        secondary_headers: Dict[int, str] = {}  # col -> 二级标题

        for col in range(1, min(30, sheet.max_column + 1)):
            value = self._get_value(sub_row, col)
            if value:
                secondary_headers[col] = str(value).strip()

        logger.info(f"二级标题: {secondary_headers}")

        # 第三步：合并成完整路径
        for col in range(1, min(30, sheet.max_column + 1)):
            if col in secondary_headers:
                primary = primary_headers.get(col, "通用")
                secondary = secondary_headers[col]
                path = f"{primary}/{secondary}"
                header_paths[col] = path
            elif col in primary_headers:
                # 一级标题没有对应的二级标题
                header_paths[col] = primary_headers[col]

        self.header_paths = {str(k): v for k, v in header_paths.items()}
        logger.info(f"Header路径: {self.header_paths}")

    def build_col_map(self) -> Dict[str, int]:
        """
        根据 Header 路径建立列映射
        """
        col_map: Dict[str, int] = {}
        used_cols: set = set()

        for col_str, path in self.header_paths.items():
            col = int(col_str)
            for col_name, patterns in COLUMN_PATTERNS.items():
                if col_name in col_map:
                    continue
                if col in used_cols:
                    continue
                for pattern, score in patterns:
                    if pattern in path or re.search(pattern, path, re.IGNORECASE):
                        col_map[col_name] = col
                        used_cols.add(col)
                        break

        self.col_map = col_map
        return col_map

    def resolve(self, sheet) -> HeaderContext:
        """
        执行完整的表头解析流程。

        Returns:
            HeaderContext 对象，包含：
            - header_row: 表头行号
            - data_start_row: 数据起始行号
            - col_map: 列映射 {字段名: 列号}
            - header_paths: Header 路径 {列号: 完整路径}
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
