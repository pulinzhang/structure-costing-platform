"""
图片处理模块

负责：
- 从 Sheet 中提取零件简图
- 将图片按行范围归属到零件号
"""

from typing import Any, Dict, List, Optional, Tuple

from app.utils.logging_config import get_logger


logger = get_logger("parser.stamping.image")


class ImageHandler:
    """图片处理器"""

    def __init__(self, header_row: int = 0):
        """
        Args:
            header_row: 表头行号，用于过滤标题区的图片
        """
        self._header_row = header_row

    def collect_images(self, sheet: Any) -> Dict[int, bytes]:
        """
        预扫描 Sheet 中的零件简图

        仅提取零件简图列（Col 3 / Col D）上的图片。
        其他位置（标题、自动化列、模板插图）的图片忽略。
        返回: Excel row(1-based) -> 图片二进制
        """
        images_by_row: Dict[int, bytes] = {}
        if not hasattr(sheet, "_images"):
            return images_by_row

        from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, TwoCellAnchor

        sketch_col = 3  # 零件简图列（0-indexed = D 列）
        count = 0
        skipped = 0

        for img in sheet._images:
            anchor = getattr(img, "anchor", None)
            if anchor is None:
                skipped += 1
                continue

            try:
                # 起始 col / row（0-indexed → 转 1-indexed）
                if isinstance(anchor, (OneCellAnchor, TwoCellAnchor)):
                    marker = anchor._from
                    if marker is None or marker.col is None or marker.row is None:
                        skipped += 1
                        continue
                    col = int(marker.col)
                    start_row = int(marker.row)
                else:
                    skipped += 1
                    continue

                # 只取零件简图列的图片
                if col != sketch_col:
                    skipped += 1
                    continue

                # 必须起始于数据区附近（≥ header_row）
                if self._header_row is not None and start_row < self._header_row:
                    skipped += 1
                    continue

                # 读取图片二进制（openpyxl 的 Image._data() 返回原始 PNG/JPEG bytes）
                img_bytes: Optional[bytes] = None
                try:
                    if hasattr(img, "_data") and callable(img._data):
                        data = img._data()
                        if isinstance(data, bytes):
                            img_bytes = data
                except Exception:
                    img_bytes = None
                # 兜底：直接从 ref 读取
                if not img_bytes:
                    ref = getattr(img, "ref", None)
                    if ref is not None and hasattr(ref, "read"):
                        try:
                            data = ref.read()
                            if isinstance(data, bytes):
                                img_bytes = data
                        except Exception:
                            img_bytes = None
                if not img_bytes:
                    skipped += 1
                    continue

                excel_row = start_row + 1
                images_by_row[excel_row] = img_bytes
                count += 1
            except Exception as e:
                logger.debug(f"读取图片失败: {e}")
                skipped += 1
                continue

        logger.info(
            f"预扫描图片: {count} 张候选 (跳过 {skipped} 张非零件图)"
        )
        return images_by_row

    def assign_to_parts(
        self,
        images_by_row: Dict[int, bytes],
        part_row_ranges: Dict[str, List[Tuple[int, int]]],
    ) -> Dict[str, bytes]:
        """
        根据行范围把图片归属到零件号

        同一零件号若多张图（数据范围被中间空白截断），保留最后一张。
        """
        result: Dict[str, bytes] = {}
        if not images_by_row or not part_row_ranges:
            return result

        assigned = 0
        unmatched: List[int] = []
        for excel_row, img_bytes in images_by_row.items():
            matched_pn: Optional[str] = None
            for pn, ranges in part_row_ranges.items():
                for (start, end) in ranges:
                    if start <= excel_row <= end:
                        matched_pn = pn
                        break
                if matched_pn:
                    break

            if matched_pn:
                result[matched_pn] = img_bytes
                assigned += 1
            else:
                unmatched.append(excel_row)

        if assigned:
            logger.info(f"图片归属: {assigned} 张已归属到零件")
        if unmatched:
            logger.warning(
                f"图片无法归属: 行 {unmatched[:10]}"
                + (f" ... 共 {len(unmatched)} 行" if len(unmatched) > 10 else "")
            )
        return result
