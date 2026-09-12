"""冲压模具费导出 — 列布局与行高（无 openpyxl）。"""

from __future__ import annotations

MAIN_COLS = 18
FEE_DETAIL_COLS = 6
FEE_END_COL = MAIN_COLS + FEE_DETAIL_COLS
COL_COUNT = 30
HEADERS = [
    "序号",
    "年度",
    "基地",
    "项目",
    "供应商",
    "版本",
    "零件号",
    "零件名称",
    "生产方式",
    "取价档",
    "材质",
    "料厚",
    "单价(万元/吨)",
    "分摊(万台)",
    "系统模具费",
    "调整金额",
    "最终模具费",
    "审核状态",
    "工序序号",
    "工序代码",
    "模具重量(T)",
    "分摊比例",
    "本序模具费",
    "费用计算依据",
    "模具编号",
    "长(mm)",
    "宽(mm)",
    "高(mm)",
    "掏空系数",
    "核对重量(T)",
]
WIDTHS = [
    6,
    8,
    10,
    12,
    18,
    10,
    16,
    18,
    12,
    10,
    10,
    8,
    14,
    12,
    14,
    12,
    14,
    10,
    10,
    10,
    12,
    10,
    14,
    40,
    16,
    10,
    10,
    10,
    10,
    14,
]

TITLE_H = 28
FILTER_H = 20
NOTE_H = 36
GROUP_H = 18
HEADER_H = 22
DATA_H = 24

FEE_HEADER_COLS = {13, 14, 15, 16, 17, 23}
MAIN_MONEY_COLS = {12, 13, 14, 15, 16, 17}
COL_LINE_FEE = 23
COL_FEE_BASIS = 24
COL_CHECK_START = FEE_END_COL + 1
COL_LENGTH = 26
COL_WIDTH = 27
COL_HEIGHT = 28
COL_HOLLOW = 29
COL_CHECK_WEIGHT = 30
FEE_MONEY_COLS = {21, 22, 23}
CHECK_NUM_COLS = {26, 27, 28, 29, 30}
CHECK_WEIGHT_FORMAT = "0.0000"
LEFT_MAIN_COLS = {3, 4, 5, 6, 8, 9, 10, 11}
BOLD_MONEY_COLS = {15, 16}
FINAL_FEE_COL = 17
PART_NUMBER_COL = 7
SEQ_COL = 1
