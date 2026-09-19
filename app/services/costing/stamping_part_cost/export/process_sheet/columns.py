"""工艺清单导出列布局。增删列先改 PROCESS_SHEET_HEADERS，再核对合并列集合。"""

from __future__ import annotations

# 拼焊总成共用列：跨子片行合并（料厚/长/宽/消耗/单价等按片分行）
_TAILOR_MERGED_COLS = frozenset(
    {
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "K",
        "Q",
        "R",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
        "AA",
        "AB",
        "AC",
        "AD",
        "AE",
        "AF",
        "AG",
        "AI",
        "AJ",
        "AL",
        "AM",
        "AN",
        "AO",
        "AP",
        "AQ",
        "AR",
        "AS",
    }
)
_NUMBER_COLS = frozenset(
    {
        "J",
        "K",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
        "AA",
        "AB",
        "AC",
        "AD",
        "AS",
    }
)
_TRACE_COLS = frozenset({"AE", "AF", "AG", "AH", "AI", "AJ", "AK", "AL", "AM", "AN", "AO"})
_ID_COLS = frozenset({"AK", "AL", "AM", "AN", "AO"})
_RESULT_COLS = frozenset({"U"})
_FINAL_COLS = frozenset({"AD"})
_FEE_RATE_COLS = frozenset({"Z", "AA", "AB", "AC"})
# 序号后的工厂/版本：弱化显示，不抢主信息
_SCOPE_WEAK_COLS = frozenset({"B", "C"})
_TEXT_LEFT_COLS = frozenset({"D", "E", "F", "G", "H", "I", "L"})
PROCESS_SHEET_HEADERS: tuple[tuple[str, str], ...] = (
    ("A", "序号"),
    ("B", "冲压工厂"),
    ("C", "版本"),
    ("D", "总成供货号"),
    ("E", "零件号"),
    ("F", "短码"),
    ("G", "零件名称"),
    ("H", "零件简图"),
    ("I", "材质"),
    ("J", "料厚"),
    ("K", "净重"),
    ("L", "零件尺寸"),
    ("M", "长"),
    ("N", "宽(步距)"),
    ("O", "可制件数"),
    ("P", "预估单件材料消耗(KG)"),
    ("Q", "材料利用率"),
    ("R", "废料重量"),
    ("S", "钢板单价(元/KG)"),
    ("T", "废料单价(元/KG)"),
    ("U", "原材料成本"),
    ("V", "加工费"),
    ("W", "模具费"),
    ("X", "检具费"),
    ("Y", "直接成本"),
    ("Z", "仓储+包装"),
    ("AA", "管理费"),
    ("AB", "财务费"),
    ("AC", "税前利润"),
    ("AD", "最终价"),
    ("AE", "来源Excel"),
    ("AF", "工作表"),
    ("AG", "行/列"),
    ("AH", "钢材价溯源"),
    ("AI", "废料价溯源"),
    ("AJ", "加工费溯源"),
    ("AK", "钢材价ID"),
    ("AL", "废料价ID"),
    ("AM", "加工费ID"),
    ("AN", "模具费ID"),
    ("AO", "检具费ID"),
    ("AP", "是否利废"),
    ("AQ", "利用哪类废料"),
    ("AR", "是否摆剪"),
    ("AS", "摆剪加价(元/吨)"),
)
_PROCESS_COL_LETTERS = tuple(letter for letter, _title in PROCESS_SHEET_HEADERS)
_FILENAME_ILLEGAL = '<>:"/\\|?*'
