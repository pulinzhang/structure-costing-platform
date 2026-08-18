"""
BOM 制造类别（冲焊件业务域）

本平台面向汽车冲压 / 焊接件供应商：
- assembly：交付客户的供货总成
- sub_assembly：分总成（焊接件，有下级子件）
- stamping：自制冲压成形件
- 不含电子件、电气件等品类

manufacturing_category 供前端展示与短零件号规则使用；
node_role（supply/structure/make/buy/consumable）仍是 BOM 结构/核价主键。
"""

from __future__ import annotations

import re
from decimal import Decimal

# 允许的制造类别（刻意不含 electronic）
MANUFACTURING_CATEGORIES = frozenset(
    {
        "assembly",
        "sub_assembly",
        "stamping",
        "standard",
        "plastic",
        "rubber",
        "consumable",
        "other",
    }
)

_STEEL_MATERIAL_KEYS = (
    "DC",
    "HC",
    "CR",
    "SPCC",
    "SPCD",
    "SPCE",
    "+Z",
    "镀锌",
    "冷轧",
    "热轧",
    "钢板",
    "B340",
    "B410",
    "SAPH",
    "QSTE",
)

_STAMPING_NAME_KEYS = (
    "支架",
    "加强板",
    "连接板",
    "内板",
    "外板",
    "梁",
    "纵梁",
    "横梁",
    "安装板",
    "固定板",
    "底板",
    "盖板",
    "罩板",
    "翼子板",
    "门槛",
)

_STANDARD_NAME_KEYS = (
    "螺母",
    "螺栓",
    "螺钉",
    "垫圈",
    "垫片",
    "卡扣",
    "卡箍",
    "铆钉",
    "销",
)

_PLASTIC_KEYS = ("塑料", "注塑", "PP", "ABS", "PC", "尼龙", "PA6", "PA66")
_RUBBER_KEYS = ("橡胶", "密封", "胶套", "减震", "EPDM", "衬套")
_CONSUMABLE_MATERIAL_KEYS = ("TEROSON", "结构胶", "密封胶", "焊丝", "涂料")

# 焊接分总成短号：
# - 无 -N：同冲压件，仅数字末四位（501005123AA → 5123）
# - 有 -N：末四位 + 字母尾 + -N（501005123AA-1 → 5123AA-1）


def short_part_number_digits(part_number: str | None) -> str | None:
    """冲压件 / 供货总成短号：数字体末四位。"""
    if not part_number:
        return None
    digits = re.sub(r"\D", "", part_number)
    if len(digits) < 4:
        return None
    return digits[-4:]


def short_weld_part_number(part_number: str | None) -> str | None:
    """
    分总成（焊接件）短号。

    - 501005123AA   → 5123
    - 501005123AA-1 → 5123AA-1
    """
    if not part_number:
        return None
    raw = str(part_number).strip()
    if not raw:
        return None
    match = re.search(r"(\d{4,})([A-Za-z]*)(-\d+)\s*$", raw)
    if match:
        digits_tail = match.group(1)[-4:]
        letters = match.group(2) or ""
        dash_suffix = match.group(3)
        return f"{digits_tail}{letters}{dash_suffix}"
    return short_part_number_digits(raw)


def resolve_manufacturing_category(
    *,
    node_role: str | None,
    is_supply_unit: bool = False,
    has_children: bool = False,
    part_name: str | None = None,
    material: str | None = None,
    part_number: str | None = None,
    thickness_mm: Decimal | None = None,
    qty_unit: str | None = None,
) -> str:
    """
    将 BOM 节点映射为冲焊件制造类别。

    规则优先级：
    1. 供货总成（交付客户）→ assembly
    2. 有下级子件 / structure / 名称含分总成 → sub_assembly（焊接分总成）
    3. make / 板料材质 / 料厚 → stamping
    4. consumable / 胶类 → consumable
    5. 标准件 / 塑料 / 橡胶
    6. buy → other；其余 other
    """
    role = (node_role or "").strip().lower()
    name = part_name or ""
    mat = material or ""
    mat_upper = mat.upper()
    pn = part_number or ""

    if is_supply_unit or role == "supply":
        return "assembly"

    if role == "structure" or has_children or ("分总成" in name):
        return "sub_assembly"

    if role == "consumable" or (qty_unit or "").lower() == "mm":
        return "consumable"

    if role == "make":
        return "stamping"

    if thickness_mm is not None:
        return "stamping"

    if mat and any(key in mat_upper for key in _STEEL_MATERIAL_KEYS):
        return "stamping"

    if any(key in name for key in _STAMPING_NAME_KEYS) and role != "buy":
        return "stamping"

    if any(key in mat_upper or key in name for key in _CONSUMABLE_MATERIAL_KEYS):
        return "consumable"

    if any(key in name for key in _STANDARD_NAME_KEYS) or pn.upper().startswith("N"):
        return "standard"

    if any(key in name or key in mat_upper for key in _PLASTIC_KEYS):
        return "plastic"

    if any(key in name or key in mat_upper for key in _RUBBER_KEYS):
        return "rubber"

    if role == "buy":
        return "other"

    if mat and role not in {"buy", "consumable"}:
        return "stamping"

    return "other"
