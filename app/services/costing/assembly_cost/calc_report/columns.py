"""计算报告 Sheet 名与核价卡列布局。"""

COVER_SHEET = "封面摘要"
CARDS_SHEET = "核价卡"
NARRATIVE_SHEET = "过程说明"

CARD_HEADERS = [
    "序号",
    "短码",
    "零件号",
    "零件名称",
    "对象类型",
    "状态",
    "材料",
    "焊接",
    "应成本",
    "间接费用",
    "总费用",
    "缺价件数",
    "说明",
    "缺价零件",
]
CARD_WIDTHS = [8, 12, 18, 22, 14, 12, 12, 12, 12, 12, 12, 10, 36, 28]
CARD_MONEY_COLS = {7, 8, 9, 10, 11}
CARD_KPI_COL = 11
CARD_STATUS_COL = 6
CARD_CENTER_COLS = {2, 12}
COVER_COL_WIDTHS = (16, 28, 16, 28)
NARRATIVE_COL_WIDTH = 120
