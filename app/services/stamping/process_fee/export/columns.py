"""冲压加工费导出 — 列布局与行高（无 openpyxl）。"""

from __future__ import annotations

MAIN_COLS = 15
COL_COUNT = 23
HEADERS = [
    "序号",
    "年度",
    "基地",
    "冲压工厂",
    "项目",
    "版本",
    "零件号",
    "短码",
    "零件名称",
    "材质",
    "料厚",
    "工序数",
    "系统计算加工费",
    "其它费用",
    "确认单价",
    "工序序号",
    "工序代码",
    "吨位(T)",
    "吨位来源",
    "费用比例",
    "冲次单价",
    "单序费用",
    "计算依据",
]
WIDTHS = [
    6,
    8,
    10,
    12,
    10,
    10,
    16,
    8,
    18,
    10,
    8,
    8,
    14,
    12,
    14,
    10,
    10,
    10,
    10,
    10,
    10,
    12,
    40,
]

TITLE_H = 28
FILTER_H = 20
NOTE_H = 20
GROUP_H = 18
HEADER_H = 22
DATA_H = 24

FEE_HEADER_COLS = {13, 14, 15, 21, 22}
LEFT_MAIN_COLS = {3, 4, 5, 6, 9, 10}
SEQ_COL = 1
PART_NUMBER_COL = 7
SHORT_CODE_COL = 8
THICKNESS_COL = 11
PROCESS_COUNT_COL = 12
SYSTEM_FEE_COL = 13
OTHER_FEE_COL = 14
FINAL_FEE_COL = 15
TONNAGE_COL = 18
RATIO_COL = 20
STROKE_PRICE_COL = 21
LINE_FEE_COL = 22
BASIS_COL = 23
