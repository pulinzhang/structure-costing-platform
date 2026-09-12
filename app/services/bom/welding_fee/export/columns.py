"""焊接费导出 — 列布局与行高（无 openpyxl）。"""

from __future__ import annotations

MAIN_COLS = 19
COL_COUNT = 26
HEADERS = [
    "序号",
    "年度",
    "基地",
    "项目",
    "版本",
    "层级",
    "零件号",
    "短代码",
    "零件名称",
    "焊接信息原文",
    "工艺数",
    "命中",
    "缺单价",
    "系统计算",
    "其它费用",
    "确认单价",
    "备注",
    "计算状态",
    "审核状态",
    "标准工艺",
    "过程量",
    "过程量单位",
    "单价",
    "单价单位",
    "行费",
    "匹配状态",
]
WIDTHS = [
    6,
    8,
    10,
    10,
    10,
    8,
    16,
    8,
    18,
    36,
    8,
    8,
    8,
    14,
    12,
    14,
    24,
    10,
    10,
    18,
    10,
    10,
    10,
    10,
    10,
    10,
]

assert len(HEADERS) == COL_COUNT
assert len(WIDTHS) == COL_COUNT
COL = {name: i for i, name in enumerate(HEADERS, start=1)}
FEE_COLS = frozenset({COL["系统计算"], COL["其它费用"], COL["确认单价"], COL["行费"]})
COUNT_COLS = frozenset({COL["工艺数"], COL["命中"], COL["缺单价"]})
LEFT_MAIN_COLS = frozenset({COL["基地"], COL["项目"], COL["版本"], COL["零件名称"], COL["备注"]})
_SCOPE_HEADERS = frozenset({"年度", "基地", "项目", "版本"})
_MAIN_HEADERS = tuple(HEADERS[:MAIN_COLS])
_DETAIL_HEADERS = tuple(HEADERS[MAIN_COLS:])
_FEE_HEADER_NAMES = ("系统计算", "其它费用", "确认单价", "行费")
_COUNT_HEADER_NAMES = ("工艺数", "命中", "缺单价")
_LEFT_MAIN_HEADER_NAMES = ("基地", "项目", "版本", "零件名称", "备注")
_WIDTH_BY_HEADER = dict(zip(HEADERS, WIDTHS, strict=True))

TITLE_H = 28
FILTER_H = 36
NOTE_H = 20
GROUP_H = 18
HEADER_H = 22
DATA_H = 26
TOTAL_H = 22
MONEY_FORMAT = "0.0000"


class WeldingSheetLayout:
    """完整列或去掉范围列（采购册范围已在表头）。"""

    def __init__(self, *, omit_scope: bool) -> None:
        main = (
            [name for name in _MAIN_HEADERS if name not in _SCOPE_HEADERS]
            if omit_scope
            else list(_MAIN_HEADERS)
        )
        self.headers = main + list(_DETAIL_HEADERS)
        self.widths = [_WIDTH_BY_HEADER[name] for name in self.headers]
        self.main_cols = len(main)
        self.col_count = len(self.headers)
        self.col = {name: index for index, name in enumerate(self.headers, start=1)}
        self.fee_cols = frozenset(self.col[name] for name in _FEE_HEADER_NAMES)
        self.count_cols = frozenset(self.col[name] for name in _COUNT_HEADER_NAMES)
        self.left_main_cols = frozenset(
            self.col[name] for name in _LEFT_MAIN_HEADER_NAMES if name in self.col
        )
        self.omit_scope = omit_scope
