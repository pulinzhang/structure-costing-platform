"""计算报告 Sheet 名与核价卡列布局。"""

COVER_SHEET = "封面摘要"
CARDS_SHEET = "核价卡"
NARRATIVE_SHEET = "过程说明"

CARD_HEADERS = [
    "序号",
    "层级",
    "树根",
    "零件号",
    "短码",
    "零件名称",
    "对象类型",
    "状态",
    "材料",
    "焊接",
    "应成本",
    "总费用",
    "缺价件数",
    "说明",
    "缺价零件",
]
CARD_WIDTHS = [6, 8, 8, 18, 10, 22, 14, 12, 12, 12, 12, 12, 10, 36, 28]
CARD_MONEY_COLS = {9, 10, 11, 12}
CARD_KPI_COL = 12
CARD_STATUS_COL = 8
CARD_CENTER_COLS = {1, 2, 3, 5, 13}
COVER_COL_WIDTHS = (16, 28, 16, 28)
NARRATIVE_COL_WIDTH = 120
