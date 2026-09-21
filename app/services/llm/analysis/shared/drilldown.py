"""单号钻取（含区间差分 period_diff）。总成与分总成分开取数。"""

from __future__ import annotations

from app.common.part_number import part_numbers_match
from app.repositories.llm.annual_part_price_analysis_repository import AnnualPartPriceRow
from app.repositories.llm.cost_analysis.rows import (
    AssemblyCardItemRow,
    L0CompositionLineRow,
    L0PartPeriodRow,
)
from app.schemas.llm.analysis_payload import DrilldownLatest, DrilldownPayload
from app.services.llm._money import money_str, month_key
from app.services.llm.analysis.shared.formulas import build_period_diff

_COST_SOURCE_LABELS = {
    "stamping": "自制冲压",
    "annual": "外购件",
    "bundle": "一口价",
    "skipped_by_bundle": "已含在一口价",
    "missing": "缺价",
    "sub_assembly": "分总成",
}

_SUPPLY_TYPE_LABELS = {
    "buy": "外购",
    "make": "自制",
    "标准件": "标准件",
    "胶块": "胶块",
}


def is_assembly_card(row: L0PartPeriodRow) -> bool:
    return bool(row.is_tree_root) or int(row.level or 0) == 0


def assembly_card_role(
    *,
    is_tree_root: bool,
    level: int,
    object_kind: str | None,
) -> str:
    """与计算过程页 object_kind / 树根口径对齐。"""
    if is_tree_root or int(level or 0) == 0:
        if object_kind == "l0_degenerate":
            return "退化供货件"
        return "供货总成"
    if object_kind == "l1_subassembly":
        return "分总成"
    if object_kind == "l1_stamping":
        return "冲压件"
    return "分总成"


def _identity_key(row: L0PartPeriodRow) -> tuple[str, bool, str, int]:
    return (
        row.part_number,
        bool(row.is_tree_root),
        row.object_kind or "",
        int(row.level or 0),
    )


def _role_sort_key(row: L0PartPeriodRow) -> tuple[int, str]:
    if row.is_tree_root or int(row.level or 0) == 0:
        return (0, row.part_number)
    if row.object_kind == "l1_subassembly":
        return (1, row.part_number)
    return (2, row.part_number)


def pick_finance_card(rows: list[L0PartPeriodRow]) -> L0PartPeriodRow:
    """与计算过程页 finance 选卡一致：同号多卡时优先树根总成。"""
    if len(rows) == 1:
        return rows[0]
    roots = [row for row in rows if row.is_tree_root]
    if roots:
        return roots[0]
    return rows[0]


def _latest_payload(row: L0PartPeriodRow) -> DrilldownLatest:
    return {
        "month": month_key(row.year, row.month),
        "year": int(row.year),
        "month_number": int(row.month),
        "grand_total": money_str(row.grand_total),
        "total_amount": money_str(row.total_amount),
        "stamping_amount": money_str(row.stamping_amount),
        "purchased_amount": money_str(row.purchased_amount),
        "bundle_amount": money_str(row.bundle_amount),
        "welding_amount": money_str(row.welding_amount),
        "welding_other_fee": money_str(row.welding_other_fee),
        "indirect_amount": money_str(row.indirect_amount),
        "calc_status": row.calc_status,
        "calc_message": row.calc_message,
        "missing_leaf_count": row.missing_leaf_count,
        "bom_version": row.bom_version,
        "location": row.location,
        "vehicle_model": row.vehicle_model,
        "card_role": assembly_card_role(
            is_tree_root=row.is_tree_root,
            level=row.level,
            object_kind=row.object_kind,
        ),
        "level": int(row.level or 0),
        "is_tree_root": bool(row.is_tree_root),
        "object_kind": row.object_kind,
        "root_part_number": row.root_part_number,
    }


def _drilldown_one_identity(rows: list[L0PartPeriodRow]) -> DrilldownPayload:
    ordered = sorted(rows, key=lambda item: (item.year, item.month))
    latest = ordered[-1]
    start_row = ordered[0]
    end_row = ordered[-1]
    points = [
        {
            "month": month_key(row.year, row.month),
            "grand_total": money_str(row.grand_total),
            "total_amount": money_str(row.total_amount),
            "calc_status": row.calc_status,
            "bom_version": row.bom_version,
            "card_role": assembly_card_role(
                is_tree_root=row.is_tree_root,
                level=row.level,
                object_kind=row.object_kind,
            ),
        }
        for row in ordered
    ]
    period_diff = build_period_diff(start_row, end_row) if ordered else None
    return {
        "kind": "drilldown",
        "part_number": latest.part_number,
        "part_name": latest.part_name,
        "card_role": assembly_card_role(
            is_tree_root=latest.is_tree_root,
            level=latest.level,
            object_kind=latest.object_kind,
        ),
        "is_tree_root": bool(latest.is_tree_root),
        "level": int(latest.level or 0),
        "object_kind": latest.object_kind,
        "root_part_number": latest.root_part_number,
        "latest": _latest_payload(latest),
        "period_diff": period_diff,
        "points": points,
    }


def build_drilldown(
    rows: list[L0PartPeriodRow],
    *,
    part_number: str,
) -> DrilldownPayload:
    matched = [row for row in rows if part_numbers_match(row.part_number, part_number)]
    if not matched:
        return {
            "kind": "drilldown",
            "part_number": part_number,
            "message": "未找到该零件号的成品核价结果（含供货总成与分总成）",
            "found": False,
            "points": [],
            "period_diff": None,
            "identities": [],
            "identity_count": 0,
        }

    assembly_rows = [row for row in matched if is_assembly_card(row)]
    branch_rows = [row for row in matched if not is_assembly_card(row)]
    primary_rows = assembly_rows or branch_rows
    fork = "assembly" if assembly_rows else "sub_assembly"

    grouped: dict[tuple[str, bool, str, int], list[L0PartPeriodRow]] = {}
    for row in primary_rows:
        grouped.setdefault(_identity_key(row), []).append(row)

    identity_heads = [pick_finance_card(items) for items in grouped.values()]
    identity_heads.sort(key=_role_sort_key)
    identities = [_drilldown_one_identity(grouped[_identity_key(head)]) for head in identity_heads]
    preferred_rows = grouped[_identity_key(pick_finance_card(identity_heads))]
    payload = _drilldown_one_identity(preferred_rows)
    payload["fork"] = fork
    payload["identities"] = identities
    payload["identity_count"] = len(identities)
    latest = payload.get("latest")
    if isinstance(latest, dict):
        payload["year"] = latest.get("year")
        payload["month"] = latest.get("month_number")
    payload["found"] = True
    payload["price_source"] = "assembly_cost_card"
    payload["price_source_label"] = "核价表"
    payload["looked_in"] = ["核价表"]
    if branch_rows and assembly_rows:
        branch_grouped: dict[tuple[str, bool, str, int], list[L0PartPeriodRow]] = {}
        for row in branch_rows:
            branch_grouped.setdefault(_identity_key(row), []).append(row)
        payload["branch_identities"] = [
            _drilldown_one_identity(items) for items in branch_grouped.values()
        ]
        payload["message"] = (
            "同一简码同时命中供货总成与分总成/子件卡，主口径按供货总成；"
            "分总成见分叉，不要混用金额"
        )
    elif fork == "sub_assembly":
        payload["message"] = "本件不是供货总成，已按分总成/子件核价卡取数"
    return payload


def cost_source_label_zh(source: str | None) -> str:
    if not source:
        return ""
    return _COST_SOURCE_LABELS.get(source, source)


def supply_type_label_zh(value: str | None) -> str:
    if not value:
        return ""
    return _SUPPLY_TYPE_LABELS.get(value, value)


def build_item_price_drilldown(
    rows: list[L0CompositionLineRow],
    *,
    part_token: str,
) -> DrilldownPayload:
    matched = [row for row in rows if part_numbers_match(row.child_part_number, part_token)]
    if not matched:
        return build_missing_part_price(part_token, costing_searched=True, annual_searched=False)
    latest = max(matched, key=lambda row: (row.year, row.month))
    at_month = [row for row in matched if row.year == latest.year and row.month == latest.month]
    parents: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for row in at_month:
        if row.root_part_number in seen:
            continue
        seen.add(row.root_part_number)
        parents.append(
            {
                "part_number": row.root_part_number,
                "part_name": row.root_part_name,
            }
        )
    head = at_month[0]
    return {
        "kind": "drilldown",
        "found": True,
        "fork": "material_line",
        "price_source": "assembly_cost_item",
        "price_source_label": "核价表",
        "looked_in": ["核价表"],
        "part_number": head.child_part_number,
        "part_name": head.child_part_name,
        "card_role": supply_type_label_zh(head.supply_type) or "材料明细",
        "year": int(head.year),
        "month": int(head.month),
        "latest": {
            "month": month_key(head.year, head.month),
            "year": int(head.year),
            "month_number": int(head.month),
            "unit_price": money_str(head.unit_price),
            "line_amount": money_str(head.line_amount),
            "location": head.location,
            "cost_source": cost_source_label_zh(head.cost_source),
            "supply_type": supply_type_label_zh(head.supply_type),
        },
        "unit_price": money_str(head.unit_price),
        "location": head.location,
        "cost_source": cost_source_label_zh(head.cost_source),
        "supply_type": supply_type_label_zh(head.supply_type),
        "parents": parents,
        "message": "本件不是供货总成卡，已按核价表材料明细取单价",
    }


def build_annual_leaf_price(
    row: AnnualPartPriceRow,
    *,
    part_token: str,
) -> DrilldownPayload:
    return {
        "kind": "drilldown",
        "found": True,
        "fork": "annual_price",
        "price_source": "annual_part_price",
        "price_source_label": "年度零件价列表",
        "looked_in": ["核价表", "年度零件价列表"],
        "part_number": row.part_number,
        "part_name": row.part_name,
        "card_role": supply_type_label_zh(row.supply_type) or "年度零件价",
        "year": int(row.year),
        "month": None,
        "latest": {
            "year": int(row.year),
            "unit_price": money_str(row.unit_price),
            "location": row.location,
            "supply_type": supply_type_label_zh(row.supply_type),
        },
        "unit_price": money_str(row.unit_price),
        "location": row.location,
        "supply_type": supply_type_label_zh(row.supply_type),
        "unit": row.unit,
        "query_token": part_token,
        "message": "核价表材料明细未命中，已按年度零件价列表取单价",
    }


def build_missing_part_price(
    part_token: str,
    *,
    costing_searched: bool = True,
    annual_searched: bool = True,
) -> DrilldownPayload:
    looked_in: list[str] = []
    if costing_searched:
        looked_in.append("核价表")
    if annual_searched:
        looked_in.append("年度零件价列表")
    return {
        "kind": "drilldown",
        "found": False,
        "fork": "missing",
        "price_source": None,
        "price_source_label": None,
        "looked_in": looked_in,
        "part_number": part_token,
        "query_token": part_token,
        "message": "核价表与年度零件价列表均未找到该零件号，按现有数据该件不存在",
    }


def build_branch_related(
    *,
    parent: L0PartPeriodRow | None,
    items: list[AssemblyCardItemRow],
) -> DrilldownPayload:
    parent_payload = None
    if parent is not None:
        parent_payload = {
            "part_number": parent.part_number,
            "part_name": parent.part_name,
            "card_role": assembly_card_role(
                is_tree_root=parent.is_tree_root,
                level=parent.level,
                object_kind=parent.object_kind,
            ),
            "year": int(parent.year),
            "month": int(parent.month),
            "month_key": month_key(parent.year, parent.month),
            "grand_total": money_str(parent.grand_total),
            "total_amount": money_str(parent.total_amount),
        }
    item_rows = [
        {
            "part_number": row.child_part_number,
            "part_name": row.child_part_name,
            "cost_source": cost_source_label_zh(row.cost_source),
            "unit_price": money_str(row.unit_price),
            "effective_qty": str(row.effective_qty),
            "line_amount": money_str(row.line_amount),
            "supply_type": row.supply_type,
            "level": int(row.node_level or 0),
        }
        for row in items
    ]
    return {
        "parent_assembly": parent_payload,
        "items": item_rows,
        "item_count": len(item_rows),
    }
