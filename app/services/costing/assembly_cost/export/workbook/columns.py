"""一览 / 材料明细 / 间接费用的列布局与表页名。"""

LIST_HEADERS = [
    "序号",
    "年度",
    "月份",
    "基地",
    "零件号",
    "短码",
    "零件名称",
    "项目",
    "版本",
    "材料",
    "焊接",
    "月总账",
    "间接",
    "总费用",
    "核算",
    "审核",
]
LIST_WIDTHS = [6, 8, 6, 10, 16, 10, 18, 10, 10, 12, 12, 12, 12, 14, 8, 8]
LIST_MONEY_COLS = {10, 11, 12, 13, 14}
LIST_KPI_COL = 14
LIST_CENTER_COLS = {1, 2, 3, 6, 15, 16}
FINANCE_LIST_SHEET = "成品核价一览"
FINANCE_ITEMS_SHEET = "成品材料明细"
FINANCE_WELDING_SHEET = "成品焊接费"
FINANCE_INDIRECTS_SHEET = "成品间接费用"

PROCUREMENT_WELD_FEE_LABEL = "焊接费/电泳黑漆等"
PROCUREMENT_LIST_HEADERS = [
    "序号",
    "短码",
    "零件号",
    "零件名称",
    "对象",
    "层级",
    "材料成本",
    PROCUREMENT_WELD_FEE_LABEL,
    "总成本",
    "确认",
    "核算",
    "审核",
]
PROCUREMENT_LIST_WIDTHS = [6, 10, 16, 22, 12, 8, 12, 16, 14, 10, 8, 8]
PROCUREMENT_LIST_MONEY_COLS = {7, 8, 9}
PROCUREMENT_LIST_KPI_COL = 9
PROCUREMENT_LIST_CENTER_COLS = {1, 2, 5, 6, 10, 11, 12}
PROCUREMENT_FILE_PREFIX = "零件成本"
PROCUREMENT_LIST_SHEET = "成本一览"
PROCUREMENT_ITEMS_SHEET = "材料明细"
PROCUREMENT_WELDING_SHEET = "焊接费"

PROCUREMENT_ITEM_HEADERS = [
    "序号",
    "短码",
    "零件号",
    "零件名称",
    "层级",
    "子件短码",
    "子件零件号",
    "子件名称",
    "取价来源",
    "匹配说明",
    "单价",
    "有效用量",
    "行金额",
]
PROCUREMENT_ITEM_WIDTHS = [6, 10, 16, 20, 8, 10, 16, 18, 14, 20, 12, 10, 12]
PROCUREMENT_ITEM_MONEY_COLS = {11, 12, 13}
PROCUREMENT_ITEM_GROUP_COLS = range(1, 5)
PROCUREMENT_ITEM_GROUP_LAST_COL = 4
PROCUREMENT_ITEM_CHILD_FIRST_COL = 5
PROCUREMENT_ITEM_PART_NUMBER_COL = 3
PROCUREMENT_ITEM_CENTER_COLS = {1, 2, 5, 6}

FINANCE_ITEM_HEADERS = [
    "序号",
    "年度",
    "月份",
    "基地",
    "项目",
    "版本",
    "核价根零件号",
    "短码",
    "层级",
    "子件零件号",
    "子件短码",
    "子件名称",
    "取价来源",
    "匹配说明",
    "单价",
    "有效用量",
    "行金额",
]
FINANCE_ITEM_WIDTHS = [6, 8, 6, 10, 10, 10, 16, 10, 8, 16, 10, 18, 14, 18, 12, 10, 12]
FINANCE_ITEM_MONEY_COLS = {15, 16, 17}

INDIRECT_HEADERS = [
    "序号",
    "年度",
    "月份",
    "基地",
    "项目",
    "版本",
    "核价根零件号",
    "短码",
    "代码",
    "名称",
    "金额",
    "费率",
    "基数",
]
INDIRECT_WIDTHS = [6, 8, 6, 10, 10, 10, 16, 10, 14, 20, 12, 10, 12]
INDIRECT_MONEY_COLS = {11, 12, 13}
