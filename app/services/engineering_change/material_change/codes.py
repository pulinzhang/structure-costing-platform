"""材料变更门禁文案。常量值就是给人看的那句，后面再补这一格该怎么改。"""

from app.common.engineering_change_gates import quoted

ECM_FILE_TYPE = "请另存为 .xlsx 再传，别的格式收不了"
ECM_SHEET_REQUIRED = (
    "请只留两张表，表名必须是「材料变更填写说明」和「工程变更单（材质）」，顺序也要一样"
)
ECM_HEADER = "请把第 1 行改成样表那十二个列名，不要在上面再加标题"
ECM_EXTRA_CELL = "请删掉十二列以外、以及最后一行零件下面多出来的字"
ECM_MERGED = "请取消合并单元格后再传"
ECM_FORMULA = "请把公式换成算好的文字再传"
ECM_SHEET_IMAGE = "请删掉贴在表上的图片再传"
ECM_EMPTY_ROW = "请从第 2 行起把零件连续写完，中间不要空一行，表也不能是空的"
ECM_CELL_TYPE = "请把这一格改成文字。数字和日期都不认"
ECM_CELL_NOT_EXACT = "请去掉这一格的前后空格和换行，空着也不能传"
ECM_EFFECTIVE_FORMAT = "请把生效年月写成「2026年6月」或「2026年06月」，也可以直接选成日期"
ECM_VERSION_FORMAT = (
    "请把变更版本写成 MAT- 加六位数字，并且和生效年月对上。2026年06月就写 MAT-202606"
)
ECM_VERSION_REQUIRED = "请整本只写一个变更版本，这一格不能空"
ECM_VERSION_DUPLICATE = "这个版本已经传过了。请换一个更晚的月份，或先到列表里删掉原来那本"
ECM_PENDING_VERSION = "这个版本正在导入，请等这次结束"
ECM_EFFECTIVE_MISMATCH = "请把生效年月改成和上传页同一个月。一本只能一个月"
ECM_PROJECT_PERIOD = "这个月这个项目还不能做材料变更"
ECM_PART_NOT_AS_OF = "这个零件在这个月没有还能用的工艺。请核对零件号，或改到它还在用的月份"
ECM_EFFECTIVE_TOO_EARLY = "请把生效年月改到工艺开始之后。工艺刚投产的那个月不能改材料"
ECM_CUTOVER_NOT_LATER = "这个零件已经有材料变更到这个月或更晚。请改到更晚的月份再传"
ECM_MIXED_WITH_REVISE = "这个零件这个月已经有设计变更。请换一个月再改材料"
ECM_TAILOR_WELD_FORBIDDEN = "拼焊件不能改材料。请把这一行删掉"
ECM_OFFAL_FORBIDDEN = "利废件不能改材料。请把这一行删掉"
ECM_BYPRODUCT_FORBIDDEN = "废料副产品不能改材料。请把这一行删掉"
ECM_AFTER_EQUALS_BEFORE = "变更前和变更后材料写成一样了。请把变更后改成要换成的牌号"
ECM_AFTER_MATERIAL_UNKNOWN = "变更后材料在材料档案里没有。请改成档案里已有的牌号，字要完全一样"
ECM_BEFORE_MATERIAL_UNKNOWN = "变更前材料在材料档案里没有。请改成档案里已有的牌号，字要完全一样"
ECM_BEFORE_MATERIAL = "变更前材料要写成这个月系统里正在用的牌号"
ECM_BEFORE_THICKNESS = "变更前料厚要写成工艺上的料厚"
ECM_THICKNESS_FORMAT = "请把料厚填成大于 0 的数字，最多两位小数，例如 1.5。不要写成文字"
ECM_THICKNESS_DELTA = "变更后料厚和变更前差得太多，超过两成了。请改近一些再传"
ECM_PROCESS_MATERIAL_CHANGED = (
    "工艺上的材料被改过，和已有的材料变更对不上。请先到列表删掉这个零件已有的材料变更，再重新传"
)
ECM_LOCATION_MISMATCH = "基地要和上传页、工艺写成同一个字。一本只能一个基地"
ECM_PROJECT_MISMATCH = "项目要和上传页、工艺写成同一个字。一本只能一个项目"
ECM_SUPPLIER_UNKNOWN = "冲压工厂请写成供应商档案里的全称，简称不行"
ECM_SUPPLIER_MISMATCH = "冲压工厂要和工艺上的全称一样。一本只能一个厂"
ECM_PART_NAME = "零件名称要和工艺上完全一样"
ECM_INTERCHANGE_REQUIRED = "互换性请写成「不影响互换性」这六个字"
ECM_DUPLICATE_CUTOVER = "同一个零件写了两行。请删掉重复的那一行"
ECM_ROLLBACK_BLOCKED = "这个零件后面还有更晚的材料变更。请先到列表删掉更晚的那本，再删这一本"

SHEET_HELP = "材料变更填写说明"
SHEET_ORDER = "工程变更单（材质）"
HEADERS = (
    "基地",
    "项目",
    "变更版本",
    "生效年月",
    "冲压工厂",
    "零件号",
    "零件名称",
    "变更前材料",
    "变更前料厚",
    "变更后材料",
    "变更后料厚",
    "互换性",
)
INTERCHANGE_REQUIRED = "不影响互换性"


def ecm_sheet(code: str, how: str = "") -> str:
    if not how:
        return code
    return f"{code}。{how}"


def ecm_row(
    code: str,
    excel_row: int,
    column: str,
    how: str = "",
    part_number: str = "",
) -> str:
    part = f"，零件{quoted(part_number)}，" if part_number else ""
    place = f"{SHEET_ORDER}第 {excel_row} 行{part}「{column}」"
    if not how:
        return f"{code}。{place}"
    return f"{code}。{place}{how}"
