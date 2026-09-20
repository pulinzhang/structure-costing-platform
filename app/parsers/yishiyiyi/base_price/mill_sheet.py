"""附页「牌号对应钢厂」：解析 Sheet2/Sheet3 文本块为牌号→钢厂（不按标题锁基地）。"""

from __future__ import annotations

import re
from typing import Any

from app.parsers.yishiyiyi.base_price.cells import cell_text

_LOCATION_IN_TITLE_RE = re.compile(r"(芜湖|大连|青岛|郑州|鄂尔多斯)(?:基地)?")
_MILL_HEADER_RE = re.compile(r"^(.+?)[:：]\s*$")
_GRADE_SPLIT_RE = re.compile(r"[、,，;\s]+")


def extract_grade_mill_map(workbook: Any) -> tuple[str | None, dict[str, str]]:
    """
    从非主表附页提取牌号→钢厂。标题里的基地名仅作识别附页用，不决定落库基地。

    返回 (标题基地片段或 None, {牌号: 钢厂})。落库基地以主表列头为准。
    标题例：``2月订单芜湖基地钢板集采牌号对应钢厂如下：``
    正文例：``马钢:`` 后跟 ``DC51D+Z、DC53D+Z``。
    """
    for sheet_name in workbook.sheetnames:
        if sheet_name in {"Sheet1", "发布价汇总价", "总价格", "汇总价格"}:
            continue
        sheet = workbook[sheet_name]
        location_hint, mapping = _parse_mill_map_sheet(sheet)
        if mapping:
            return location_hint, mapping
    return None, {}


def _parse_mill_map_sheet(sheet: Any) -> tuple[str | None, dict[str, str]]:
    location_hint: str | None = None
    mapping: dict[str, str] = {}
    current_mill: str | None = None

    for row in sheet.iter_rows(values_only=True):
        text = cell_text(row[0]) if row else ""
        if not text:
            continue

        if location_hint is None and ("牌号对应钢厂" in text or "对应钢厂" in text):
            match = _LOCATION_IN_TITLE_RE.search(text)
            if match:
                location_hint = match.group(1)
            continue

        mill_match = _MILL_HEADER_RE.match(text)
        if mill_match:
            current_mill = mill_match.group(1).strip()
            continue

        if current_mill is None:
            continue

        for grade in _GRADE_SPLIT_RE.split(text):
            grade = grade.strip().rstrip("、,，;")
            if not grade or grade.endswith(":"):
                continue
            mapping[grade.replace("//", "/")] = current_mill

    return location_hint, mapping
