"""总成核价计算过程（detail_text + 可筛选卡片 JSON）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TypedDict

from app.common.money import Q4, optional_format_money

MISSING_PART_LIMIT = 12
CONFLICT_LIMIT = 30


class CardTracePayload(TypedDict):
    part_number: str
    part_name: str | None
    level: int
    is_tree_root: bool
    object_kind: str | None
    status: str
    should_cost: str | None
    grand_total: str | None
    material_amount: str | None
    welding_amount: str | None
    missing_leaf_count: int
    message: str | None
    missing_parts: list[str]


def _money(value: Decimal | None) -> str | None:
    return optional_format_money(value, Q4, 4)


@dataclass
class ProcessLogBuilder:
    _lines: list[str] = field(default_factory=list)
    _cards: list[CardTracePayload] = field(default_factory=list)

    def line(self, message: str) -> None:
        self._lines.append(message)

    def section(self, title: str) -> None:
        self._lines.append("")
        self._lines.append(f"=== {title} ===")

    def error(self, message: str) -> None:
        self._lines.append(f"[错误] {message}")

    def warn(self, message: str) -> None:
        self._lines.append(f"[警告] {message}")

    def add_card(
        self,
        *,
        part_number: str,
        part_name: str | None,
        level: int,
        is_tree_root: bool,
        object_kind: str | None,
        status: str,
        should_cost: Decimal | None = None,
        grand_total: Decimal | None = None,
        material_amount: Decimal | None = None,
        welding_amount: Decimal | None = None,
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
            "status": status,
            "should_cost": _money(should_cost),
            "grand_total": _money(grand_total),
            "material_amount": _money(material_amount),
            "welding_amount": _money(welding_amount),
            "missing_leaf_count": missing_leaf_count,
            "message": message,
            "missing_parts": parts,
        }
        self._cards.append(payload)
        flag = status.upper()
        name = part_name or "—"
        extra = f" {message}" if message else ""
        self.line(
            f"[{flag}] L{level} {part_number} {name} "
            f"应成本={payload['should_cost'] or '—'} "
            f"总费用={payload['grand_total'] or '—'} "
            f"缺叶={missing_leaf_count}{extra}"
        )

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
                "missing_leaf_count": int(item.get("missing_leaf_count") or 0),
                "message": str(item["message"]) if item.get("message") else None,
                "missing_parts": missing_parts,
            }
        )
    return cards
