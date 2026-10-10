"""总成核价计算过程（给人看的说明 + 可筛选卡片 JSON）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TypedDict

from app.common.money import Q4, optional_format_money
from app.services.costing.assembly_cost.codes import PURCHASED_ASSEMBLY_NOTE

MISSING_PART_LIMIT = 12
CONFLICT_LIMIT = 30

_MISSING_HINT_LABEL = {
    "missing": "缺价",
    "multi_supplier_unit_cost": "价冲突",
}


class CardTracePayload(TypedDict):
    part_number: str
    part_name: str | None
    level: int
    is_tree_root: bool
    object_kind: str | None
    seq_label: str
    source_node_id: int | None
    status: str
    should_cost: str | None
    grand_total: str | None
    material_amount: str | None
    welding_amount: str | None
    indirect_amount: str | None
    missing_leaf_count: int
    message: str | None
    missing_parts: list[str]


def _money(value: Decimal | None) -> str | None:
    return optional_format_money(value, Q4, 4)


def format_missing_part_label(part_number: str, match_hint: str | None) -> str:
    key = match_hint or "missing"
    reason = _MISSING_HINT_LABEL.get(key, key)
    return f"{part_number}（{reason}）"


def compose_card_message(
    *,
    status: str,
    missing_leaf_count: int = 0,
    weld_incomplete: bool = False,
    is_purchased_assembly: bool = False,
    extra: str | None = None,
) -> str | None:
    """卡片说明：短句。缺价件号由卡片自己的 missing_parts 携带。

    外购件总成（P4）价齐时写 PURCHASED_ASSEMBLY_NOTE，核算报告「说明」列用同一句。
    """
    if extra:
        return extra
    if status == "skipped":
        return "已审核，跳过"
    if status == "ok":
        return PURCHASED_ASSEMBLY_NOTE if is_purchased_assembly else None
    chunks: list[str] = []
    if missing_leaf_count > 0:
        chunks.append(f"缺价 {missing_leaf_count}，补冲压价/年度价后重算")
    if weld_incomplete:
        chunks.append("焊接费不完整")
    if status == "partial" and not chunks:
        chunks.append("价不齐")
    return "；".join(chunks) if chunks else None


def _unique_constraint_clause(text: str) -> str:
    """只取约束字段那一行，避免 INSERT 列清单里误伤 part_number。"""
    marker = "UNIQUE constraint failed:"
    start = text.find(marker)
    if start < 0:
        return ""
    rest = text[start + len(marker) :]
    for stop in ("\n", "[SQL", "("):
        cut = rest.find(stop)
        if cut >= 0:
            rest = rest[:cut]
    return rest.strip()


def operator_write_error(exc: BaseException, *, part_number: str) -> str:
    """落库失败：禁止把 SQL / 堆栈甩给操作员。"""
    text = str(exc)
    name = type(exc).__name__
    is_unique = (
        name == "IntegrityError"
        or "UNIQUE constraint" in text
        or "unique constraint" in text.lower()
        or "IntegrityError" in text
    )
    clause = _unique_constraint_clause(text)
    if is_unique and "part_number" in clause:
        return f"{part_number} 零件号冲突，未保存"
    if is_unique and "source_node_id" in clause:
        return f"{part_number} BOM 节点已有卡，未保存"
    if is_unique:
        return f"{part_number} 写入冲突，未保存"
    return f"{part_number} 计算失败，未保存"


@dataclass
class ProcessLogBuilder:
    _lines: list[str] = field(default_factory=list)
    _cards: list[CardTracePayload] = field(default_factory=list)

    def line(self, message: str) -> None:
        self._lines.append(message)

    def section(self, title: str) -> None:
        self._lines.append("")
        self._lines.append(f"【{title}】")

    def error(self, message: str) -> None:
        self._lines.append(f"错误：{message}")

    def warn(self, message: str) -> None:
        self._lines.append(f"注意：{message}")

    def add_card(
        self,
        *,
        part_number: str,
        part_name: str | None,
        level: int,
        is_tree_root: bool,
        object_kind: str | None,
        seq_label: str = "",
        source_node_id: int | None = None,
        status: str,
        should_cost: Decimal | None = None,
        grand_total: Decimal | None = None,
        material_amount: Decimal | None = None,
        welding_amount: Decimal | None = None,
        indirect_amount: Decimal | None = None,
        missing_leaf_count: int = 0,
        message: str | None = None,
        missing_parts: list[str] | None = None,
    ) -> None:
        parts = list(missing_parts or [])
        payload: CardTracePayload = {
            "part_number": part_number,
            "part_name": part_name,
            "level": level,
            "is_tree_root": is_tree_root,
            "object_kind": object_kind,
            "seq_label": seq_label,
            "source_node_id": source_node_id,
            "status": status,
            "should_cost": _money(should_cost),
            "grand_total": _money(grand_total),
            "material_amount": _money(material_amount),
            "welding_amount": _money(welding_amount),
            "indirect_amount": _money(indirect_amount),
            "missing_leaf_count": missing_leaf_count,
            "message": message,
            "missing_parts": parts,
        }
        self._cards.append(payload)

    def build_text(self) -> str:
        return "\n".join(self._lines).strip() + ("\n" if self._lines else "")

    def build_json(self) -> str:
        return json.dumps(self._cards, ensure_ascii=False)


def parse_card_traces(raw: str | None) -> list[CardTracePayload]:
    if not raw:
        return []
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    cards: list[CardTracePayload] = []
    for item in loaded:
        if not isinstance(item, dict):
            continue
        part_number = item.get("part_number")
        status = item.get("status")
        if not isinstance(part_number, str) or not isinstance(status, str):
            continue
        missing_raw = item.get("missing_parts") or []
        missing_parts = [str(p) for p in missing_raw] if isinstance(missing_raw, list) else []
        level_raw = item.get("level")
        cards.append(
            {
                "part_number": part_number,
                "part_name": str(item["part_name"]) if item.get("part_name") is not None else None,
                "level": int(level_raw) if isinstance(level_raw, int) else 0,
                "is_tree_root": bool(item.get("is_tree_root")),
                "object_kind": str(item["object_kind"]) if item.get("object_kind") else None,
                "seq_label": str(item["seq_label"]) if item.get("seq_label") else "",
                "source_node_id": int(item["source_node_id"])
                if isinstance(item.get("source_node_id"), int)
                else None,
                "status": status,
                "should_cost": str(item["should_cost"])
                if item.get("should_cost") is not None
                else None,
                "grand_total": str(item["grand_total"])
                if item.get("grand_total") is not None
                else None,
                "material_amount": str(item["material_amount"])
                if item.get("material_amount") is not None
                else None,
                "welding_amount": str(item["welding_amount"])
                if item.get("welding_amount") is not None
                else None,
                "indirect_amount": str(item["indirect_amount"])
                if item.get("indirect_amount") is not None
                else None,
                "missing_leaf_count": int(item.get("missing_leaf_count") or 0),
                "message": str(item["message"]) if item.get("message") else None,
                "missing_parts": missing_parts,
            }
        )
    return cards
