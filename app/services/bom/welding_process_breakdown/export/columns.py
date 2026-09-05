"""
L0 核对导出 — 列布局与文案常量（无 openpyxl 依赖）
"""

from __future__ import annotations

TITLE_H = 38
FILTER_H = 22
NOTE_H = 24
GROUP_H = 22
HEADER_H = 32
DATA_H = 34

PARSE_LABEL = {
    "ok": "正常",
    "partial": "部分识别",
    "unparsed": "未识别",
    "anomaly": "异常",
}
MAP_LABEL = {
    "ready": "已对齐",
    "ambiguous": "待定",
    "unmapped": "未映射",
}

# 主表 1–10；明细 11–22
MAIN_COLS = 10
HEADERS = [
    "序号",
    "基地",
    "项目",
    "版本",
    "零件号",
    "短代码",
    "零件名称",
    "焊接原文",
    "工艺数",
    "解析状态",
    "行号",
    "原文工艺",
    "命中片段",
    "标准工艺",
    "标准单位",
    "过程量",
    "单位",
    "次要过程量",
    "次要单位",
    "计费用量",
    "计费单位",
    "映射状态",
]
COL_COUNT = len(HEADERS)
assert COL_COUNT == 22

COL: dict[str, int] = {name: i for i, name in enumerate(HEADERS, start=1)}
STD_COLS = frozenset({COL["标准工艺"], COL["标准单位"]})
BILLING_COLS = frozenset({COL["计费用量"], COL["计费单位"]})
QTY_COLS = frozenset({COL["过程量"], COL["次要过程量"], COL["计费用量"]})
PART_COLS = frozenset({COL["零件号"], COL["短代码"]})
CENTER_COLS = frozenset(
    {
        COL["序号"],
        COL["短代码"],
        COL["工艺数"],
        COL["解析状态"],
        COL["行号"],
        COL["标准单位"],
        COL["单位"],
        COL["次要单位"],
        COL["计费单位"],
        COL["映射状态"],
    }
)
MUTED_QTY_COLS = frozenset(
    {
        COL["过程量"],
        COL["次要过程量"],
        COL["单位"],
        COL["次要单位"],
    }
)

NOTE = (
    "黄列=计费用量（有次要则用次要）。红列=标准工艺/单位。"
    "例：焊缝：2条(52mm) → CO2焊缝·CM，计费52mm，核价时 mm→CM(÷10)。"
)

WIDTHS = [
    6,
    8,
    8,
    8,
    16,
    8,
    16,
    34,
    7,
    9,
    5,
    10,
    14,
    20,
    8,
    8,
    6,
    10,
    7,
    10,
    8,
    8,
]

assert len(WIDTHS) == COL_COUNT

SHEET_TITLE = "L0工艺核对"
REPORT_TITLE = "焊接工艺拆解 · L0 过程量核对表"
GROUP_MAIN = "零件信息"
GROUP_DETAIL = "工艺明细 · 核对区（红=标准 · 黄=计费）"
