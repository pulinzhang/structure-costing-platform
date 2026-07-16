"""
冲压工艺 Excel 文件解析器 V6
企业级生产级解析器

核心设计：Header Context 路径匹配
不再分别处理一级/二级标题，而是将它们合并成完整路径：
- 工艺/工序号
- 工艺/代号
- 设备/吨位
- 模具/类型
"""

import re
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional, Tuple, Set
import openpyxl

from app.utils.logging_config import get_logger


logger = get_logger("parser.stamping")


@dataclass
class ParserResult:
    """解析结果统一封装"""
    parts: List[Dict[str, Any]] = field(default_factory=list)
    processes: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    sheet_name: str = ""
    header_row: int = 0
    data_start_row: int = 0
    col_map: Dict[str, int] = field(default_factory=dict)
    header_paths: Dict[str, str] = field(default_factory=dict)  # col -> "一级/二级"

    total_rows: int = 0
    parse_time_ms: float = 0

    @property
    def part_count(self) -> int:
        return len(self.parts)

    @property
    def process_count(self) -> int:
        return len(self.processes)

    def log_summary(self) -> None:
        logger.info(f"=== 解析完成 ===")
        logger.info(f"Sheet: {self.sheet_name}")
        logger.info(f"表头行: {self.header_row}, 数据起始行: {self.data_start_row}")
        logger.info(f"零件数: {self.part_count}, 工序数: {self.process_count}")
        logger.info(f"Header路径: {self.header_paths}")
        logger.info(f"列映射: {self.col_map}")
        if self.warnings:
            logger.warning(f"警告: {len(self.warnings)} 个")
            for w in self.warnings[:5]:
                logger.warning(f"  - {w}")


class StampingExcelParser:
    """
    冲压工艺 Excel 解析器 V6
    """

    # Header Context 路径匹配模式
    # 格式: "一级/二级" 或 "字段名"
    COLUMN_PATTERNS = {
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
            ("料片长", 1000), ("长", 700),
        ],
        "width": [
            ("料片宽", 1000), ("宽", 700),
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

    def __init__(self):
        self.result = ParserResult()
        self.merged_cache: Dict[Tuple[int, int], Any] = {}

    def parse(self, file_path: str) -> ParserResult:
        """解析冲压工艺 Excel 文件"""
        import time
        start_time = time.time()

        logger.info(f"开始解析冲压工艺文件: {file_path}")

        self.result = ParserResult()
        self.merged_cache = {}

        try:
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            sheet = self._find_stamping_sheet(workbook)

            if not sheet:
                raise ValueError("未找到冲压工艺数据Sheet")

            self.result.sheet_name = sheet.title
            self._build_merged_cache(sheet)

            # 构建 Header Context
            header_row = self._find_header_row(sheet)
            self.result.header_row = header_row
            self.result.data_start_row = header_row + 2

            # 构建完整路径映射
            self._build_header_context(sheet, header_row)

            # 建立列映射
            self.result.col_map = self._build_col_map()

            logger.info(f"表头行: {self.result.header_row}, 数据起始行: {self.result.data_start_row}")
            logger.info(f"Header路径: {self.result.header_paths}")
            logger.info(f"列映射: {self.result.col_map}")

            # 解析数据
            process_count = defaultdict(int)
            current_part: Optional[Dict[str, Any]] = None

            for row_idx in range(self.result.data_start_row, sheet.max_row + 1):
                self.result.total_rows += 1

                part_no = self._get_value(sheet, row_idx, self.result.col_map.get("part_no", 2))
                op = self._get_value(sheet, row_idx, self.result.col_map.get("op", 12))

                if self._is_part_row(part_no):
                    if current_part and current_part.get("part_number"):
                        self._save_part(current_part, process_count)
                        self.result.parts.append(current_part)
                    current_part = self._parse_part_row(sheet, row_idx)
                    process_count[current_part["part_number"]] = 0

                    if self._is_process_row(op):
                        process = self._parse_process(sheet, row_idx, current_part["part_number"])
                        if process:
                            self.result.processes.append(process)
                            process_count[current_part["part_number"]] += 1
                    continue

                if current_part and self._is_process_row(op):
                    process = self._parse_process(sheet, row_idx, current_part["part_number"])
                    if process:
                        self.result.processes.append(process)
                        process_count[current_part["part_number"]] += 1

            if current_part and current_part.get("part_number"):
                self._save_part(current_part, process_count)
                self.result.parts.append(current_part)

            self.result.parse_time_ms = (time.time() - start_time) * 1000
            self.result.log_summary()

            return self.result

        except Exception as e:
            logger.error(f"解析文件失败: {e}")
            raise

    def _find_stamping_sheet(self, workbook) -> Optional[openpyxl.worksheet.worksheet.Worksheet]:
        """识别冲压数据Sheet"""
        for sheet in workbook.worksheets:
            for row_idx in range(1, min(16, sheet.max_row + 1)):
                row_values = [self._get_value(sheet, row_idx, col) for col in range(1, 25)]
                row_text = " ".join([str(v) for v in row_values if v])

                has_part = any(p in row_text for p in ["零件号", "件号", "Part No"])
                has_op = any(p in row_text for p in ["工序", "OP", "Process"])

                if has_part and has_op:
                    logger.info(f"找到数据Sheet: {sheet.title}, 行{row_idx}")
                    return sheet

        return workbook.active

    def _build_merged_cache(self, sheet) -> None:
        """建立合并单元格缓存"""
        for merged_range in sheet.merged_cells.ranges:
            min_r, min_c = merged_range.min_row, merged_range.min_col
            value = sheet.cell(min_r, min_c).value

            for r in range(min_r, merged_range.max_row + 1):
                for c in range(min_c, merged_range.max_col + 1):
                    self.merged_cache[(r, c)] = value

    def _find_header_row(self, sheet) -> int:
        """
        找到表头起始行
        通过检查是否存在"零件号"等关键字段
        """
        for row_idx in range(1, 20):
            for col in range(1, min(30, sheet.max_column + 1)):
                text = self._get_value(sheet, row_idx, col)
                if text and ("零件号" in str(text) or "零件编号" in str(text)):
                    logger.info(f"找到表头行: {row_idx}")
                    return row_idx
        return 4

    def _build_header_context(self, sheet, header_row: int) -> None:
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
                value = self._get_value(sheet, header_row, min_c)
                if value:
                    # 这个合并区域下的所有列都归属于这个一级标题
                    for c in range(min_c, max_c + 1):
                        primary_headers[c] = str(value).strip()

        # 也检查非合并的一级标题
        for col in range(1, min(30, sheet.max_column + 1)):
            if col not in primary_headers:
                value = self._get_value(sheet, header_row, col)
                if value:
                    primary_headers[col] = str(value).strip()

        logger.info(f"一级标题: {primary_headers}")

        # 第二步：扫描二级标题
        sub_row = header_row + 1
        secondary_headers: Dict[int, str] = {}  # col -> 二级标题

        for col in range(1, min(30, sheet.max_column + 1)):
            value = self._get_value(sheet, sub_row, col)
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

        self.result.header_paths = header_paths
        logger.info(f"Header路径: {header_paths}")

    def _build_col_map(self) -> Dict[str, int]:
        """
        根据 Header 路径建立列映射
        """
        col_map: Dict[str, int] = {}

        for col, path in self.result.header_paths.items():
            for col_name, patterns in self.COLUMN_PATTERNS.items():
                if col_name in col_map:
                    continue

                for pattern, score in patterns:
                    # 检查路径是否匹配
                    if pattern in path or re.search(pattern, path, re.IGNORECASE):
                        col_map[col_name] = col
                        break

        return col_map

    def _get_value(self, sheet, row: int, col: int) -> Any:
        """获取单元格值"""
        cache_key = (row, col)
        if cache_key in self.merged_cache:
            return self.merged_cache[cache_key]
        return sheet.cell(row, col).value

    def _is_part_row(self, value: Any) -> bool:
        """判断零件行"""
        if not value:
            return False

        val_str = str(value).strip()

        exclude = [r"^序号?$", r"^零件号?$", r"^名称$", r"^合计", r"^备注",
                   r"^总计", r"^平均", r"^小计", r"^零件", r"^工序", r"^$"]
        for p in exclude:
            if re.match(p, val_str):
                return False

        if len(val_str) >= 6 and re.match(r"^[A-Za-z0-9]+$", val_str):
            if re.search(r"[A-Za-z]", val_str) and re.search(r"[0-9]", val_str):
                return True

        return False

    def _is_process_row(self, value: Any) -> bool:
        """判断工序行"""
        if not value:
            return False
        return bool(re.match(r"^OP\d+$", str(value).strip(), re.IGNORECASE))

    def _parse_part_row(self, sheet, row_idx: int) -> Dict[str, Any]:
        """解析零件行"""
        col_map = self.result.col_map

        return {
            "seq_no": self._parse_int(self._get_value(sheet, row_idx, col_map.get("seq", 1))),
            "part_number": self._get_value(sheet, row_idx, col_map.get("part_no", 2)),
            "part_name": self._get_value(sheet, row_idx, col_map.get("part_name", 3)),
            "material": self._get_value(sheet, row_idx, col_map.get("material", 5)),
            "thickness": self._parse_decimal(self._get_value(sheet, row_idx, col_map.get("thickness", 6))),
            "part_weight": self._parse_decimal(self._get_value(sheet, row_idx, col_map.get("weight", 7))),
            "sheet_length": self._parse_decimal(self._get_value(sheet, row_idx, col_map.get("length", 8))),
            "sheet_width": self._parse_decimal(self._get_value(sheet, row_idx, col_map.get("width", 9))),
            "parts_per_sheet": self._parse_int(self._get_value(sheet, row_idx, col_map.get("count", 10))),
            "sheet_type": self._get_value(sheet, row_idx, col_map.get("sheet_type", 11)),
            "tonnage": self._parse_decimal(self._get_value(sheet, row_idx, col_map.get("tonnage", 15))),
            "die_type": self._get_value(sheet, row_idx, col_map.get("die_type", 16)),
            "process_method": self._get_value(sheet, row_idx, col_map.get("method", 17)),
            "automation": self._get_value(sheet, row_idx, col_map.get("auto", 18)),
            "remark": self._get_value(sheet, row_idx, col_map.get("remark", 19)),
        }

    def _parse_process(self, sheet, row_idx: int, part_number: str) -> Optional[Dict[str, Any]]:
        """解析工序行"""
        col_map = self.result.col_map
        op = self._get_value(sheet, row_idx, col_map.get("op", 12))
        code = self._get_value(sheet, row_idx, col_map.get("code", 13))

        if not op:
            return None

        if not code:
            self.result.warnings.append(f"零件 {part_number} 的 {op} 缺少工艺代码")

        return {
            "part_number": part_number,
            "process_seq": str(op).strip(),
            "process_code": code,
            "die_sets": self._parse_int(self._get_value(sheet, row_idx, col_map.get("die_set", 14))),
            "tonnage": self._parse_decimal(self._get_value(sheet, row_idx, col_map.get("tonnage", 15))),
            "remark": self._get_value(sheet, row_idx, col_map.get("remark", 19)),
        }

    def _save_part(self, part: Dict[str, Any], process_count: Dict[str, int]) -> None:
        """保存零件"""
        part_no = part.get("part_number")
        count = process_count.get(part_no, 0)

        if count == 0:
            self.result.warnings.append(f"零件 {part_no} 没有任何工序")
        elif count == 1:
            self.result.warnings.append(f"零件 {part_no} 只有1道工序")

    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """解析数值"""
        if value is None:
            return None

        val_str = str(value).strip()
        if not val_str:
            return None

        val_str = re.sub(r"[^0-9.\-/~]", "", val_str)

        if not val_str:
            return None

        if "/" in val_str:
            parts = val_str.split("/")
            try:
                val_str = str(float(parts[0]) / float(parts[1]))
            except (ValueError, ZeroDivisionError):
                pass

        if "~" in val_str:
            val_str = val_str.split("~")[0].strip()

        try:
            return Decimal(val_str)
        except (InvalidOperation, ValueError):
            return None

    def _parse_int(self, value: Any) -> Optional[int]:
        """解析整数"""
        if value is None:
            return None
        val_str = str(value).strip()
        if not val_str:
            return None
        try:
            if "." in val_str:
                return int(float(val_str))
            return int(val_str)
        except (ValueError, InvalidOperation):
            return None


def parse_stamping_excel(file_path: str) -> ParserResult:
    """便捷函数"""
    parser = StampingExcelParser()
    return parser.parse(file_path)
