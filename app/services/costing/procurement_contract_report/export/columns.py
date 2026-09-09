"""协议 Excel 文案与列布局（不访问 DB、不渲染）。"""

AGREEMENT_SHEET_TITLE = "批量零部件价格协议"
ANNEX_LABEL = "附件二"
TITLE = AGREEMENT_SHEET_TITLE
CURRENCY_LABEL = "币种：人民币"
TAX_EXCLUDED_NOTE = "价格均不含增值税"
PAGE_NUMBER_FOOTER = "第 &P/&N 页"
QTY_UNIT = "件"
NUMBER_LABEL = "编号："
EMPTY_BODY = "以下空白"
NOTES_LABEL = "其他说明："
REMARK_LABEL = "备注："
PAY_SEPARATELY = "N"
MISSING_VALUE = "/"

FIXED_HEADERS = (
    (1, "序号"),
    (2, "存货编码"),
    (3, "零件号"),
    (4, "零件名称"),
    (5, "单车\n数量"),
    (6, "计量\n单位"),
)

SINGLE_MONTH_PRICE_HEADER = "结算价格\n（元）"
TOOLING_GROUP_HEADER = "工装费"
PAY_SEPARATELY_HEADER = "单独支\n付Y/N"
ALLOC_GROUP_HEADER = "单件工装分摊价格（元/件）"
ALLOC_PRICE_HEADER = "分摊价格（元/件）"
TOOLING_FEE_HEADER = "工装费\n（元）"
ALLOC_QTY_HEADER = "分摊数量\n（件）"
REMARK_COL_HEADER = "备注"
