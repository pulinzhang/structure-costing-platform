"""钢价政策 Excel 文件解析器。

架构（编排器 + Sheet 处理器）：

    SteelPricePolicyExcelParser  ←  编排器：负责加载 Excel、聚合结果
        ↓
        parse_steel_price_policy_sheet(sheet, sheet_name)
        ↓
    find_handler(sheet_name).parse(sheet, steel_mill, warnings)
        ↓
    BaseSheetHandler.parse() → List[ParsedPolicy]

子模块:
    value_parser.py     单元格值解析（数字、字符串、str）
    boundary_parser.py  列头区间解析（≥0.5, ≤950mm, 1000-1600 等）
    handlers/           每个 Sheet 排版一个处理器
    models/             ParsedPolicy, ParsedLadderItem, SheetParseResult

支持 .xlsx 和 .xls 两种 Excel 格式：
- .xlsx 使用 openpyxl 读取
- .xls 使用 xlrd 读取，内部转换为 openpyxl Worksheet 兼容格式

约定：
- 一次只处理一张 Sheet：调用方（service）控制循环，便于持久化单张 Sheet
- 新增钢厂只需新增 handler，找不到处理器时回退到 DefaultSheetHandler
"""

import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

import xlrd
from openpyxl.worksheet.worksheet import Worksheet

from app.utils.logging_config import get_logger

from .handlers.registry import find_handler
from .models.parse_result import SteelPricePolicyParseResult

# progress_callback(progress: int, msg: str) — 可选进度回调
ProgressCallback = Callable[[int, str], None]

logger = get_logger("parser.steel_price_policy")

# ============================================================================
# Sheet 兼容层：统一 xlrd sheet → openpyxl Worksheet 接口
# ============================================================================


class _XlrdSheetWrapper:
    """将 xlrd sheet 包装为 openpyxl Worksheet 接口，供 handler 直接使用。

    Handler 读取单元格的方式统一为：
        cell.value        → 获取单元格值（str/float/int/空字符串）
        cell.ctype        → xlrd 单元格类型（忽略，部分 handler 用不到）
        row[c].value      → 第 c 列的值
        sheet.max_row     → 最大行数
        sheet.max_column  → 最大列数
        sheet.cell(r, c).value → 单元格值
        sheet.merged_cells → 合并单元格集合（空集合，与 openpyxl 兼容）
    """

    def __init__(self, xlrd_sheet: xlrd.sheet.Sheet) -> None:
        self._sheet = xlrd_sheet
        self.max_row = xlrd_sheet.nrows
        self.max_column = xlrd_sheet.ncols
        self.name = xlrd_sheet.name

    @property
    def merged_cells(self) -> Any:
        """返回空集合，与 openpyxl 合并单元格接口兼容。"""
        return set()

    def cell(self, row: int, column: int) -> Any:
        """返回单元格值（与 openpyxl sheet.cell(row, col) 接口兼容）。"""
        return _XlrdCellWrapper(self._sheet, row - 1, column - 1)

    def __iter__(self) -> Any:
        for row_idx in range(self.max_row):
            yield _XlrdRowWrapper(self._sheet, row_idx)

    def __getitem__(self, coord: str) -> Any:
        return self._sheet.cell_by_addr(*self._parse_coord(coord))

    def _parse_coord(self, coord: str) -> Any:
        col_str, row_str = "", ""
        for ch in coord:
            if ch.isalpha():
                col_str += ch
            else:
                row_str += ch
        col = 0
        for ch in col_str.upper():
            col = col * 26 + (ord(ch) - ord("A") + 1)
        return int(row_str) - 1, col - 1


class _XlrdRowWrapper:
    def __init__(self, sheet: xlrd.sheet.Sheet, row_idx: int) -> None:
        self._sheet = sheet
        self.row_idx = row_idx

    def __iter__(self) -> Any:
        for col in range(self._sheet.ncols):
            yield _XlrdCellWrapper(self._sheet, self.row_idx, col)

    def __getitem__(self, col_idx: int) -> Any:
        return _XlrdCellWrapper(self._sheet, self.row_idx, col_idx)


class _XlrdCellWrapper:
    def __init__(self, sheet: xlrd.sheet.Sheet, row_idx: int, col_idx: int) -> None:
        self._sheet = sheet
        self.row_idx = row_idx
        self.col_idx = col_idx
        cell = sheet.cell(row_idx, col_idx)
        self.value = _unwrap_xlrd_cell(cell)

    @property
    def ctype(self) -> Any:
        return self._sheet.cell(self.row_idx, self.col_idx).ctype


def _unwrap_xlrd_cell(cell: Any) -> Any:
    """将 xlrd 单元格值转为 Python 原生类型（str/float/int/None）。"""
    ctype, value = cell.ctype, cell.value
    if ctype == xlrd.XL_CELL_EMPTY:
        return None
    if ctype == xlrd.XL_CELL_TEXT:
        return str(value).strip() if value else None
    if ctype == xlrd.XL_CELL_NUMBER:
        if value == int(value):
            return int(value)
        return value
    if ctype == xlrd.XL_CELL_DATE:
        from xlrd.xldate import XLDateAmbiguous, XLDateNegative, XLDateOOD

        try:
            tuple_val = xlrd.xldate_as_tuple(value, 0)
            if tuple_val[0] == 0 and tuple_val[1] == 0:
                return float(value)
            return f"{tuple_val[0]}-{tuple_val[1]:02d}-{tuple_val[2]:02d}"
        except (XLDateAmbiguous, XLDateNegative, XLDateOOD):
            return float(value)
    if ctype == xlrd.XL_CELL_BOOLEAN:
        return bool(value)
    if ctype == xlrd.XL_CELL_ERROR:
        return None
    if ctype == xlrd.XL_CELL_BLANK:
        return None
    return value


# ============================================================================
# 单 Sheet 解析（核心 API，一次处理一张 Sheet）
# ============================================================================


def parse_steel_price_policy_sheet(
    sheet: Worksheet,
    sheet_name: str,
    warnings: list[str],
    excel_filename: str | None = None,
) -> Any:
    """解析一张 Sheet，返回 ParsedPolicy 列表。

    设计要点：
    - 一次只处理一张 Sheet（一个钢厂）
    - 调用方（service 层）负责 db.commit() 持久化
    - 调用方负责多 Sheet 的迭代
    - 新增钢厂时只需新增 handler，本函数无需修改

    Args:
        sheet: openpyxl Worksheet 对象
        sheet_name: Sheet 名字（== 钢厂名）
        warnings: 调用方的警告列表（用作告警输入）
        excel_filename: 来源 Excel 文件名（用于测试核对）

    Returns:
        该 Sheet 包含的所有 ParsedPolicy
    """
    handler = find_handler(sheet_name)
    try:
        policies = handler.parse(sheet, sheet_name, warnings)
        for policy in policies:
            policy.excel_filename = excel_filename
            policy.sheet_name = sheet_name
        logger.info(f"钢厂 [{sheet_name}] 解析完成，共 {len(policies)} 条政策")
        return policies
    except Exception as e:
        msg = f"钢厂 [{sheet_name}] 解析失败: {e}"
        logger.error(msg)
        warnings.append(msg)
        return []


# ============================================================================
# 多 Sheet 编排（便捷 API，一次解析整张 Excel 并聚合）
# ============================================================================


def parse_steel_price_policy_excel(
    file: str | Path | bytes,
    *,
    year: int,
    month: int,
    excel_filename: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> SteelPricePolicyParseResult:
    """整张 Excel 解析（便捷 API）。

    内部按 Sheet 依次调用 parse_steel_price_policy_sheet，
    并聚合到 SteelPricePolicyParseResult。

    等价于：
        result = SteelPricePolicyParseResult(year=..., month=...)
        for sheet in wb:
            policies = parse_steel_price_policy_sheet(sheet, sheet.name, result.warnings)
            result.policies.extend(policies)
    """
    parser = SteelPricePolicyExcelParser(
        year=year,
        month=month,
        excel_filename=excel_filename,
        progress_callback=progress_callback,
    )
    return parser.parse(file)


# ============================================================================
# 编排器
# ============================================================================


class SteelPricePolicyExcelParser:
    """钢价政策 Excel 编排器（按 Sheet 依次解析，聚合结果）。"""

    def __init__(
        self,
        *,
        year: int,
        month: int,
        excel_filename: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ):
        self.year = year
        self.month = month
        self.excel_filename = excel_filename
        self.progress_callback = progress_callback
        self.result = SteelPricePolicyParseResult()

    def _report(self, progress: int, msg: str) -> None:
        if self.progress_callback:
            self.progress_callback(progress, msg)

    def parse(self, file: str | Path | bytes) -> SteelPricePolicyParseResult:
        logger.info(f"开始解析钢价政策 Excel（{self.year}年{self.month}月）")
        self.result = SteelPricePolicyParseResult(year=self.year, month=self.month)

        self._report(5, "正在读取 Excel 字节流...")
        wb, _ = _load_workbook_or_bytes(file)
        try:
            self.result.sheet_names = list(wb.sheetnames)
            total_sheets = len(wb.sheetnames) or 1
            # === 关键：按 Sheet 逐张处理 ===
            for index, sheet_name in enumerate(wb.sheetnames):
                # 解析阶段占用 5% ~ 70%
                progress = 5 + int((index / total_sheets) * 65)
                self._report(
                    progress, f"正在解析 Sheet：{sheet_name}（{index + 1}/{total_sheets}）"
                )
                sheet = wb[sheet_name]
                policies = parse_steel_price_policy_sheet(
                    sheet, sheet_name, self.result.warnings, excel_filename=self.excel_filename
                )
                self.result.policies.extend(policies)
            self._report(70, f"解析完成，共 {len(self.result.policies)} 条政策，准备写入数据库...")
            self._log_summary()
            return self.result
        finally:
            wb.close()

    def _log_summary(self) -> None:
        n_t = sum(1 for p in self.result.policies if p.policy_type == "THICKNESS")
        n_w = sum(1 for p in self.result.policies if p.policy_type == "WIDTH")
        logger.info("=== 钢价政策解析完成 ===")
        logger.info(
            f"钢厂 sheet 数: {len(self.result.sheet_names)}, "
            f"厚度政策: {n_t}, 宽度政策: {n_w}, "
            f"警告: {len(self.result.warnings)} 条"
        )


# ============================================================================
# Excel 加载辅助（兼容 path / bytes 两种入参，支持 .xlsx / .xls）
# ============================================================================


class _WorkbookWrapper:
    """统一 .xlsx / .xls 两种格式的 Workbook 接口。

    接口：
        sheetnames   → List[str]
        __iter__     → 按顺序遍历 sheet 名称
        __getitem__  → 按名称获取 sheet（返回 SheetWrapper）
        close()      → 关闭资源
    """

    def __init__(self, wb: Any, is_xls: bool = False) -> None:
        self._wb = wb
        self.is_xls = is_xls

    @property
    def sheetnames(self) -> Any:
        return self._wb.sheet_names() if self.is_xls else self._wb.sheetnames

    def __iter__(self) -> Any:
        return iter(self.sheetnames)

    def __getitem__(self, name: str) -> Any:
        raw = self._wb.sheet_by_name(name) if self.is_xls else self._wb[name]
        if self.is_xls:
            return _XlrdSheetWrapper(raw)
        return raw

    def close(self) -> None:
        self._wb.release_resources() if self.is_xls else self._wb.close()


def _load_workbook_or_bytes(file: Any) -> tuple[Any, ...]:
    """加载 workbook，自动识别 .xlsx / .xls 格式。

    Returns:
        (_WorkbookWrapper, path_or_none)
    """
    from openpyxl import load_workbook

    if isinstance(file, str | Path):
        path = Path(file)
        if path.suffix.lower() == ".xls":
            xlrd_wb = xlrd.open_workbook(str(path))
            return _WorkbookWrapper(xlrd_wb, is_xls=True), path
        wb = load_workbook(str(path), data_only=True)
        return _WorkbookWrapper(wb, is_xls=False), path

    if isinstance(file, bytes):
        if file[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            xlrd_wb = xlrd.open_workbook(file_contents=file)
            return _WorkbookWrapper(xlrd_wb, is_xls=True), None
        wb = load_workbook(io.BytesIO(file), data_only=True)
        return _WorkbookWrapper(wb, is_xls=False), None

    raise TypeError(f"file must be path or bytes, got {type(file).__name__}")
