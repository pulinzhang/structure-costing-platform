"""采购对象清单导出 — 列布局（无 openpyxl）。"""

from __future__ import annotations

COL_COUNT = 24
GROUP_ROW = 4
HEADER_ROW = 5
DATA_START = 6

GROUP_SPANS = (
    (1, 6, "对着原件"),
    (7, 8, "供货总成"),
    (9, 12, "判定"),
    (13, 17, "佐证"),
    (18, 20, "原件补充"),
    (21, 24, "范围"),
)

HEADERS = (
    "Excel行号",
    "工作表",
    "零件号",
    "短码",
    "内部号",
    "零件名称",
    "供货总成零件号",
    "供货总成名称",
    "对象种类",
    "确认",
    "供应商",
    "审核",
    "材料",
    "料厚",
    "厂家",
    "焊接信息",
    "备注",
    "退化亚类",
    "层级",
    "原始文件名",
    "基地",
    "项目",
    "BOM版本",
    "生失效",
)
WIDTHS = (
    12,
    12,
    18,
    8,
    14,
    22,
    18,
    22,
    12,
    10,
    22,
    10,
    12,
    10,
    14,
    28,
    22,
    12,
    8,
    28,
    10,
    10,
    12,
    22,
)
SHEET_COL = 2
L0_NO_COL = 7
L0_NAME_COL = 8
CONFIRM_COL = 10
FILENAME_COL = 20
SHORT_CODE_COL = 4
INTERNAL_NUMBER_COL = 5
PRIMARY_COLS = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12})
CENTER_COLS = frozenset({1, 2, 4, 9, 10, 12, 19})
KEY_COLS = frozenset({1, 3, 7})
L0_COLS = (L0_NO_COL, L0_NAME_COL)

JUDGE_END_COL = 12
KPI_COLS = frozenset({10})
EVIDENCE_START_COL = 13
