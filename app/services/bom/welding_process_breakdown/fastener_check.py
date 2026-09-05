"""
子件紧固件用量校验（相对单件 process_qty）

仅用于核对：不参与计费乘数。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app.models.bom import BomNode

_FASTENER_NAME_RE = re.compile(r"螺母|螺栓|螺柱|植焊|凸焊|铆|支撑柱|搭铁", re.I)
_FASTENER_PN_RE = re.compile(r"^(N|Q|QR|FQ)", re.I)

# 需要与子件用量交叉核对的工艺
CHECKABLE_TOKENS = frozenset({"凸焊", "植焊", "铆接", "搭铁"})
_CHECKABLE_TOKENS = CHECKABLE_TOKENS  # 兼容旧引用


@dataclass(frozen=True)
class FastenerQtyCheckResult:
    """子件用量 vs 单件过程量"""

    child_fastener_qty_sum: Decimal | None
    qty_check_status: str  # skipped / no_child / match / mismatch
    qty_check_detail: str | None


def sum_child_fastener_qty(
    children: list[BomNode],
) -> tuple[Decimal | None, str | None]:
    """汇总子级疑似被焊件/紧固件用量。"""
    if not children:
        return None, None
    parts: list[str] = []
    total = Decimal("0")
    for child in children:
        name = f"{child.part_name or ''} {child.part_number or ''}"
        if _FASTENER_NAME_RE.search(name) or _FASTENER_PN_RE.match(child.part_number or ""):
            qty = child.qty if child.qty is not None else Decimal("0")
            total += qty
            parts.append(f"{child.part_number}×{qty}")
    if not parts:
        return None, None
    return total, "；".join(parts)


def check_process_qty_against_children(
    *,
    process_token: str,
    process_qty: Decimal,
    children: list[BomNode],
) -> FastenerQtyCheckResult:
    """
    将明细单件过程量与子件用量对照。

    非核对类工艺 → skipped。
    """
    if process_token not in _CHECKABLE_TOKENS or process_qty <= 0:
        return FastenerQtyCheckResult(None, "skipped", None)

    fastener_sum, detail = sum_child_fastener_qty(children)
    if fastener_sum is None:
        return FastenerQtyCheckResult(None, "no_child", None)
    if fastener_sum == process_qty:
        return FastenerQtyCheckResult(fastener_sum, "match", detail)
    return FastenerQtyCheckResult(
        fastener_sum,
        "mismatch",
        f"process_qty={process_qty} vs 子件={fastener_sum}; {detail or ''}",
    )
