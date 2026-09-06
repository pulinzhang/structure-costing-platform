"""采购对象清单 — 对人展示的文案（内部码仍用 other_leaf / l0_degenerate）。

Excel 工作表名不能含 `/`，标准件分区表名用「标准件及胶等」；单元格与页面用「标准件/胶等」。
"""

from app.services.bom.procurement_object.classify import (
    KIND_L0_DEGENERATE,
    KIND_L1_STAMPING,
    KIND_L1_SUBASSEMBLY,
    SECTION_ANOMALY,
    SECTION_OBJECT,
    SECTION_OTHER_LEAF,
)

KIND_LABELS = {
    KIND_L0_DEGENERATE: "退化供货件",
    KIND_L1_SUBASSEMBLY: "分总成",
    KIND_L1_STAMPING: "冲压件",
}

SECTION_LABELS = {
    SECTION_OBJECT: "采购对象",
    SECTION_OTHER_LEAF: "标准件/胶等",
    SECTION_ANOMALY: "异常",
}

SECTION_SHEET_TITLES = {
    SECTION_OBJECT: "采购对象",
    SECTION_OTHER_LEAF: "标准件及胶等",
    SECTION_ANOMALY: "异常",
}

SUBTYPE_LABELS = {
    "special_process": "特殊工艺",
    "stamping_blank": "冲压毛坯",
}

CONFIRM_LABELS = {
    "pending": "待定",
    "outsourced": "外发",
    "in_house": "自制",
}

AUDIT_LABELS = {
    "pending": "待审",
    "approved": "已审",
}
