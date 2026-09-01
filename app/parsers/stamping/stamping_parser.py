"""
冲压工艺 Excel 文件解析器

解析流程（与 README.md 保持一致）：
1. 加载 Excel → ExcelContext.load()
2. 识别 Sheet → HeaderResolver.find_stamping_sheet()
3. 解析表头 → HeaderResolver.resolve()
4. 建立零件号合并缓存 → ExcelContext.build_merged_cache(part_no_col)
5. 解析数据行 → 遍历零件号范围，提取零件/工序数据

设计原则：
- 先确定结构（表头），再处理数据（缓存）
- 图片归属在解析数据行时顺便完成
- 工序代码为空时，该零件工序结束
"""

import time
from typing import Any

from app.exceptions.base import BusinessException
from app.parsers.stamping.excel_context import ExcelContext
from app.parsers.stamping.header_resolver import HeaderResolver
from app.parsers.stamping.models.header import HeaderContext
from app.parsers.stamping.models.parse_result import ParserResult
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.parsers.stamping.row_parser import (
    PartSaver,
    RowParser,
)
from app.utils.logging_config import get_logger

logger = get_logger("parser.stamping")


class StampingExcelParser:
    """
    冲压工艺 Excel 解析器 V6

    架构：各模块各司其职，由 Parser 统一编排。

    数据流：
    Excel
        ↓
    ExcelContext（加载文件、访问单元格）
        ↓
    HeaderContext（表头信息）
        ↓
    PartNoRange（零件号范围）
        ↓
    Part（零件）/ Process（工序）
        ↓
    ParserResult（最终结果）
    """

    def __init__(self) -> None:
        self.result = ParserResult()
        self._excel_ctx: ExcelContext | None = None
        self._header_resolver: HeaderResolver | None = None
        self._row_parser: RowParser | None = None
        self._processed_images: set[Any] = set()  # 已处理图片集合，避免重复

    def parse(self, file_path: str) -> ParserResult:
        """解析冲压工艺 Excel 文件"""
        start_time = time.time()
        logger.info(f"开始解析冲压工艺文件: {file_path}")

        self.result = ParserResult()
        part_saver = PartSaver()

        try:
            # === 第一阶段：初始化 ===
            self._init_parsers(file_path)

            # === 第二阶段：解析数据 ===
            self._parse_data(part_saver)

            # === 第三阶段：收尾 ===
            self.result.parse_time_ms = (time.time() - start_time) * 1000
            self._log_summary()
            return self.result

        except Exception as e:
            logger.error(f"解析文件失败: {e}")
            raise
        finally:
            if self._excel_ctx:
                self._excel_ctx.close()

    def _init_parsers(self, file_path: str) -> None:
        """初始化各模块"""
        # Excel 上下文
        self._excel_ctx = ExcelContext()
        self._excel_ctx.load(file_path)

        # 先识别 Sheet（但还不知道表头在哪行）
        self._excel_ctx.find_sheet()
        self.result.sheet_name = self._excel_ctx.sheet.title

        # 初始化 HeaderResolver（需要先创建才能使用）
        self._header_resolver = HeaderResolver(self._excel_ctx.get_value)

        # 提取冲压供应商名称
        stamping_supplier = self._header_resolver.find_stamping_supplier(self._excel_ctx.sheet)
        if stamping_supplier:
            self.result.stamping_supplier = stamping_supplier
            logger.info(f"冲压供应商: {stamping_supplier}")
        # 提取车型信息,即项目名称
        vehicle_model = self._header_resolver.find_stamping_vehicle_model(self._excel_ctx.sheet)
        if vehicle_model:
            self.result.vehicle_model = vehicle_model
            logger.info(f"从Excel提取车型: {vehicle_model}")

        # 提取版本
        version = self._header_resolver.find_stamping_project_version(self._excel_ctx.sheet)
        if version:
            self.result.version = version
            logger.info(f"从Excel提取版本: {version}")
        # 解析表头
        header_ctx: HeaderContext = self._header_resolver.resolve(self._excel_ctx.sheet)

        self.result.header_row = header_ctx.header_row
        self.result.data_start_row = header_ctx.data_start_row
        self.result.col_map = header_ctx.col_map
        self.result.header_paths = header_ctx.header_paths
        if "die_number" not in header_ctx.col_map:
            raise BusinessException("未识别到「模具编号」列，请确认工艺确认表含该列")

        logger.info(f"表头行: {self.result.header_row}, 数据起始行: {self.result.data_start_row}")

        # 表头确定后，建立零件号合并缓存
        part_no_col = header_ctx.col_map.get("part_no", 2)
        self._excel_ctx.build_merged_cache(part_no_col)

        # 行解析器
        self._row_parser = RowParser(self._excel_ctx.get_value, header_ctx.col_map)

    def _parse_data(self, part_saver: PartSaver) -> None:
        """解析数据主循环：遍历零件号范围"""
        excel_ctx = self._excel_ctx
        col_map = self.result.col_map
        data_start = self.result.data_start_row

        process_count: dict[str, int] = {}
        current_part_number: str | None = None

        for row_idx in range(data_start, excel_ctx.sheet.max_row + 1):
            self.result.total_rows += 1

            # 获取该行的零件号范围
            part_range = excel_ctx.get_part_no_range(row_idx)

            if part_range:
                # 零件行：只在范围的起始行处理
                if row_idx == part_range.start_row:
                    part_no = part_range.value

                    # 保存上一个零件
                    if current_part_number and current_part_number != part_no:
                        self._save_part(
                            current_part_number, part_saver, process_count, self.result.warnings
                        )

                    current_part_number = part_no
                    if part_no not in process_count:
                        process_count[part_no] = 0

                    # 解析零件行，直接存储 Part 对象
                    part: Part = self._row_parser.parse_part_row(row_idx)
                    part.excel_sheet_name = self.result.sheet_name or None
                    self.result.parts.append(part)

                    # 图片归属（传入完整零件范围，确保覆盖合并行的所有可能位置）
                    self._handle_image_for_row(row_idx, part_no, part_range.end_row)

                # 该行属于零件范围，检查是否有工序（只用 op 列判断）
                op_val = excel_ctx.get_value(row_idx, col_map.get("op", 12))

                if current_part_number and op_val:
                    # 有工序代码
                    process: Process | None = self._row_parser.parse_process_row(
                        row_idx, current_part_number
                    )
                    if process:
                        self.result.processes.append(process)
                        process_count[current_part_number] += 1

            # 非零件号行不做处理（页脚等区域会被跳过）

        # 保存最后一个零件
        if current_part_number:
            self._save_part(current_part_number, part_saver, process_count, self.result.warnings)

    def _save_part(
        self,
        part_number: str,
        part_saver: PartSaver,
        process_count: dict[str, int],
        warnings: list[str],
    ) -> None:
        """保存零件（生成警告）"""
        part_saver.save_part(part_number, process_count.get(part_number, 0), warnings)

    def _handle_image_for_row(self, row_idx: int, part_number: str | None, end_row: int) -> None:
        """处理该行的图片归属

        Excel 排版规则（基于 excel_sample 样本）：
        - 简图固定在 D 列（0-indexed col=3）
        - 图片锚点可能在零件起始行、零件范围中间任意行、或零件结束行的下一行
          （因为合并单元格会导致图片锚点偏移）

        openpyxl 的 anchor._from.col / _from.row 都是 0-indexed，
        调用方 row_idx 是 1-indexed 的 Excel 行号。
        """
        if not part_number:
            return

        sheet = self._excel_ctx.sheet
        if not hasattr(sheet, "_images"):
            return

        # 0-indexed：Excel 的 D 列（"零件简图"列固定位置）
        sketch_col_0idx = 3

        for img in sheet._images:
            # 跳过已有归属的图片
            if img in getattr(self, "_processed_images", set()):
                continue

            anchor = getattr(img, "anchor", None)
            if anchor is None:
                continue

            try:
                from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, TwoCellAnchor

                if isinstance(anchor, OneCellAnchor | TwoCellAnchor):
                    marker = anchor._from
                    if marker is None or marker.col is None or marker.row is None:
                        continue
                    col_0idx = int(marker.col)
                    start_row_0idx = int(marker.row)
                else:
                    continue

                if col_0idx != sketch_col_0idx:
                    continue

                # 行匹配：0-indexed 图片行 与 1-indexed 范围的比较
                # 图片行 8 (0-indexed) -> Excel row 9
                # 零件范围 7-13 -> 0-indexed: 6-12
                # 允许匹配：图片行在零件范围内（start_row-1 <= img_row < end_row）
                img_row_0idx = start_row_0idx
                part_start_0idx = row_idx - 1
                part_end_0idx = end_row - 1

                if not (part_start_0idx <= img_row_0idx <= part_end_0idx):
                    continue

                img_bytes = None
                if hasattr(img, "_data") and callable(img._data):
                    data = img._data()
                    if isinstance(data, bytes):
                        img_bytes = data
                if not img_bytes:
                    ref = getattr(img, "ref", None)
                    if ref and hasattr(ref, "read"):
                        data = ref.read()
                        if isinstance(data, bytes):
                            img_bytes = data

                if img_bytes:
                    self.result.images_by_part[part_number] = img_bytes
                    # 标记为已处理，避免重复
                    if not hasattr(self, "_processed_images"):
                        self._processed_images = set()
                    self._processed_images.add(img)
            except Exception:
                continue

    def _log_summary(self) -> None:
        """输出解析摘要"""
        logger.info("=== 解析完成 ===")
        logger.info(f"Sheet: {self.result.sheet_name}")
        logger.info(f"表头行: {self.result.header_row}, 数据起始行: {self.result.data_start_row}")
        logger.info(
            f"零件数: {self.result.part_count}, 工序数: {self.result.process_count}, 简图: {self.result.image_count}"
        )
        logger.info(f"Header路径: {self.result.header_paths}")
        logger.info(f"列映射: {self.result.col_map}")
        if self.result.warnings:
            logger.warning(f"警告: {len(self.result.warnings)} 个")
            for w in self.result.warnings[:5]:
                logger.warning(f"  - {w}")


def parse_stamping_excel(file_path: str) -> ParserResult:
    """便捷函数"""
    parser = StampingExcelParser()
    return parser.parse(file_path)
