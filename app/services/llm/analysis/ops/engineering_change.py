"""工程变更 summary / drilldown / 变更前后单价比较。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
)
from app.common.part_number import normalize_part_number_token, part_numbers_match
from app.repositories.llm.cost_analysis.rows import L0PartPeriodRow
from app.repositories.llm.engineering_change_analysis_repository import EngineeringChangeRow
from app.repositories.llm.procurement_object_analysis_repository import ProcurementObjectRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
from app.schemas.llm.analysis_payload import (
    DrilldownPayload,
    RiskEntry,
    RiskPayload,
    SummaryPayload,
)
from app.services.llm._money import money_str, month_key

_SAMPLE_LIMIT = 50
_PRICE_LOOKBACK_MONTHS = 12

# 口语「停用件」= 完成停止（整总成）+ 此件不装（少装一颗）
DISCONTINUE_CHANGE_TYPES: tuple[str, ...] = (CHANGE_TYPE_STOP, CHANGE_TYPE_NOT_INSTALL)


def _ym_key(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def _from_ym_key(key: int) -> tuple[int, int]:
    return key // 12, key % 12 + 1


def _as_object_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _affected_part_number(row: EngineeringChangeRow) -> str:
    return (
        (row.after_part_number or "").strip()
        or (row.before_part_number or "").strip()
        or (row.after_assembly_part_number or "").strip()
        or row.before_assembly_part_number
    )


def _item_from_row(row: EngineeringChangeRow) -> dict[str, str | int | None]:
    return {
        "change_type": row.change_type,
        "before_part_number": row.before_part_number,
        "after_part_number": row.after_part_number,
        "part_name": row.part_name,
        "before_assembly_part_number": row.before_assembly_part_number,
        "after_assembly_part_number": row.after_assembly_part_number,
        "assembly_name": row.assembly_name,
        "part_level": row.part_level,
        "location": row.location,
        "vehicle_model": row.vehicle_model,
        "project_code": row.project_code,
        "effective_year": row.effective_year,
        "effective_month": row.effective_month,
    }


def compare_pair_numbers(row: EngineeringChangeRow) -> tuple[str | None, str | None, str]:
    """优先零件级前后号；没有则用总成号。"""
    before_part = (row.before_part_number or "").strip() or None
    after_part = (row.after_part_number or "").strip() or None
    if before_part or after_part:
        return before_part, after_part, "part"
    before_asm = (row.before_assembly_part_number or "").strip() or None
    after_asm = (row.after_assembly_part_number or "").strip() or None
    return before_asm, after_asm, "assembly"


def collect_compare_part_numbers(rows: Sequence[EngineeringChangeRow]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for row in rows:
        before, after, _grain = compare_pair_numbers(row)
        for token in (before, after):
            if not token:
                continue
            key = normalize_part_number_token(token)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(token)
    return ordered


def _assembly_unit_price(row: L0PartPeriodRow) -> Decimal:
    if row.should_cost is not None:
        return Decimal(str(row.should_cost))
    return Decimal(str(row.grand_total or 0))


def _pick_assembly_side(
    candidates: Sequence[L0PartPeriodRow],
    *,
    part_number: str,
    prefer: str,
    effective_year: int,
    effective_month: int,
) -> dict[str, object] | None:
    matched = [row for row in candidates if part_numbers_match(row.part_number, part_number)]
    if not matched:
        return None
    eff_key = _ym_key(effective_year, effective_month)
    if prefer == "before":
        pool = [row for row in matched if _ym_key(row.year, row.month) < eff_key]
        if not pool:
            pool = list(matched)
        picked = max(pool, key=lambda row: (row.year, row.month))
        price_label = "应成本"
        price = _assembly_unit_price(picked)
        if picked.should_cost is None:
            price_label = "总费用"
    else:
        pool = [row for row in matched if _ym_key(row.year, row.month) >= eff_key]
        if not pool:
            pool = list(matched)
        picked = min(pool, key=lambda row: (row.year, row.month))
        price_label = "应成本"
        price = _assembly_unit_price(picked)
        if picked.should_cost is None:
            price_label = "总费用"
    return {
        "part_number": picked.part_number,
        "part_name": picked.part_name,
        "month": month_key(picked.year, picked.month),
        "unit_price": money_str(price),
        "price_label": price_label,
        "price_source": "总成核价卡",
        "calc_status": picked.calc_status,
        "bom_version": picked.bom_version,
    }


def _pick_stamping_side(
    candidates: Sequence[StampingPartPeriodRow],
    *,
    part_number: str,
    prefer: str,
    effective_year: int,
    effective_month: int,
) -> dict[str, object] | None:
    matched = [row for row in candidates if part_numbers_match(row.part_number, part_number)]
    if not matched:
        return None
    eff_key = _ym_key(effective_year, effective_month)
    if prefer == "before":
        pool = [row for row in matched if _ym_key(row.year, row.month) < eff_key]
        if not pool:
            pool = list(matched)
        picked = max(pool, key=lambda row: (row.year, row.month))
    else:
        pool = [row for row in matched if _ym_key(row.year, row.month) >= eff_key]
        if not pool:
            pool = list(matched)
        picked = min(pool, key=lambda row: (row.year, row.month))
    return {
        "part_number": picked.part_number,
        "part_name": picked.part_name,
        "month": month_key(picked.year, picked.month),
        "unit_price": money_str(picked.unit_cost),
        "price_label": "冲压单价",
        "price_source": "冲压零件价格一览",
        "calc_status": picked.calc_status,
        "bom_version": None,
    }


def _pick_side(
    *,
    part_number: str | None,
    prefer: str,
    effective_year: int,
    effective_month: int,
    assembly_by_part: Mapping[str, Sequence[L0PartPeriodRow]],
    stamping_by_part: Mapping[str, Sequence[StampingPartPeriodRow]],
) -> dict[str, object] | None:
    if not part_number:
        return None
    key = normalize_part_number_token(part_number)
    assembly_side = _pick_assembly_side(
        assembly_by_part.get(key, ()),
        part_number=part_number,
        prefer=prefer,
        effective_year=effective_year,
        effective_month=effective_month,
    )
    if assembly_side is not None:
        return assembly_side
    return _pick_stamping_side(
        stamping_by_part.get(key, ()),
        part_number=part_number,
        prefer=prefer,
        effective_year=effective_year,
        effective_month=effective_month,
    )


def _composition_snapshot(
    side: dict[str, object] | None, row: L0PartPeriodRow | None
) -> dict[str, str] | None:
    if side is None or row is None:
        return None
    if side.get("price_source") != "总成核价卡":
        return None
    return {
        "stamping_amount": money_str(row.stamping_amount),
        "purchased_amount": money_str(row.purchased_amount),
        "welding_amount": money_str(row.welding_amount),
        "bundle_amount": money_str(row.bundle_amount),
        "indirect_amount": money_str(row.indirect_amount),
        "should_cost": money_str(
            row.should_cost if row.should_cost is not None else row.grand_total
        ),
    }


def _pick_assembly_row(
    candidates: Sequence[L0PartPeriodRow],
    *,
    part_number: str,
    prefer: str,
    effective_year: int,
    effective_month: int,
) -> L0PartPeriodRow | None:
    matched = [row for row in candidates if part_numbers_match(row.part_number, part_number)]
    if not matched:
        return None
    eff_key = _ym_key(effective_year, effective_month)
    if prefer == "before":
        pool = [row for row in matched if _ym_key(row.year, row.month) < eff_key]
        if not pool:
            pool = list(matched)
        return max(pool, key=lambda row: (row.year, row.month))
    pool = [row for row in matched if _ym_key(row.year, row.month) >= eff_key]
    if not pool:
        pool = list(matched)
    return min(pool, key=lambda row: (row.year, row.month))


def build_engineering_change_price_comparison(
    rows: list[EngineeringChangeRow],
    *,
    assembly_by_part: Mapping[str, Sequence[L0PartPeriodRow]],
    stamping_by_part: Mapping[str, Sequence[StampingPartPeriodRow]],
    sample_limit: int = _SAMPLE_LIMIT,
    jump_threshold: Decimal = Decimal("0.10"),
) -> SummaryPayload:
    """变更前号 vs 变更后号：各取生效月两侧最近核价卡比较。"""
    items: list[dict[str, object]] = []
    both_priced = 0
    missing_before = 0
    missing_after = 0
    after_priced = 0
    after_unpriced = 0
    jump_up_items: list[dict[str, object]] = []
    for row in rows:
        before_no, after_no, grain = compare_pair_numbers(row)
        if not before_no and not after_no:
            continue
        before_side = _pick_side(
            part_number=before_no,
            prefer="before",
            effective_year=row.effective_year,
            effective_month=row.effective_month,
            assembly_by_part=assembly_by_part,
            stamping_by_part=stamping_by_part,
        )
        after_side = _pick_side(
            part_number=after_no,
            prefer="after",
            effective_year=row.effective_year,
            effective_month=row.effective_month,
            assembly_by_part=assembly_by_part,
            stamping_by_part=stamping_by_part,
        )
        before_asm_row = (
            _pick_assembly_row(
                assembly_by_part.get(normalize_part_number_token(before_no), ()),
                part_number=before_no,
                prefer="before",
                effective_year=row.effective_year,
                effective_month=row.effective_month,
            )
            if before_no
            else None
        )
        after_asm_row = (
            _pick_assembly_row(
                assembly_by_part.get(normalize_part_number_token(after_no), ()),
                part_number=after_no,
                prefer="after",
                effective_year=row.effective_year,
                effective_month=row.effective_month,
            )
            if after_no
            else None
        )
        if before_no and before_side is None:
            missing_before += 1
        if after_no and after_side is None:
            missing_after += 1
            after_unpriced += 1
        elif after_no and after_side is not None:
            after_priced += 1
        delta: str | None = None
        delta_rate: str | None = None
        is_jump_up = False
        if before_side is not None and after_side is not None:
            both_priced += 1
            before_price = Decimal(str(before_side["unit_price"]))
            after_price = Decimal(str(after_side["unit_price"]))
            change = after_price - before_price
            delta = money_str(change)
            if before_price != 0:
                rate = change / before_price
                delta_rate = money_str(rate)
                is_jump_up = rate >= jump_threshold
        composition_before = _composition_snapshot(before_side, before_asm_row)
        composition_after = _composition_snapshot(after_side, after_asm_row)
        composition_delta: dict[str, str] | None = None
        if composition_before and composition_after:
            composition_delta = {
                key: money_str(
                    Decimal(str(composition_after[key])) - Decimal(str(composition_before[key]))
                )
                for key in (
                    "stamping_amount",
                    "purchased_amount",
                    "welding_amount",
                    "bundle_amount",
                    "indirect_amount",
                    "should_cost",
                )
            }
        note = None
        if row.change_type == CHANGE_TYPE_STOP:
            note = "完成停止：通常只有变更前价"
        elif row.change_type == CHANGE_TYPE_NOT_INSTALL:
            note = "此件不装：变更后零件号为空，只有变更前价"
        elif before_no and after_no and before_side is None and after_side is None:
            note = "变更前后均未找到核价卡"
        elif before_no and before_side is None:
            note = "变更前无核价卡"
        elif after_no and after_side is None:
            note = "变更后无核价卡"
        item: dict[str, object] = {
            "change_type": row.change_type,
            "part_level": row.part_level,
            "compare_grain": grain,
            "part_name": row.part_name or row.assembly_name,
            "location": row.location,
            "vehicle_model": row.vehicle_model,
            "effective_month": month_key(row.effective_year, row.effective_month),
            "before_part_number": before_no,
            "after_part_number": after_no,
            "before": before_side,
            "after": after_side,
            "delta": delta,
            "delta_rate": delta_rate,
            "is_jump_up": is_jump_up,
            "composition_before": composition_before,
            "composition_after": composition_after,
            "composition_delta": composition_delta,
            "note": note,
        }
        items.append(item)
        if is_jump_up:
            jump_up_items.append(item)
        if len(items) >= sample_limit:
            break
    return {
        "kind": "comparison",
        "subject": "engineering_change_price",
        "purpose": "工程变更零件：变更前号 vs 变更后号单价比较",
        "price_rule": (
            f"变更前取生效月之前最近一张卡（最多往前{_PRICE_LOOKBACK_MONTHS}个月）；"
            "变更后取生效月起最近一张卡；优先总成核价应成本，其次冲压零件单价"
        ),
        "jump_threshold": money_str(jump_threshold),
        "row_count": len(items),
        "both_priced_count": both_priced,
        "missing_before_count": missing_before,
        "missing_after_count": missing_after,
        "after_priced_count": after_priced,
        "after_unpriced_count": after_unpriced,
        "jump_up_count": len(jump_up_items),
        "jump_up_items": jump_up_items[:sample_limit],
        "sample_truncated": len(rows) > sample_limit,
        "items": items,
        "message": (
            f"可比较 {both_priced} 对；变更前缺价 {missing_before}，变更后缺价 {missing_after}；"
            f"涨超 {money_str(jump_threshold)} 的 {len(jump_up_items)} 对"
            if items
            else "当前范围无可用的变更前后零件号"
        ),
    }


def price_window_for_rows(
    rows: Sequence[EngineeringChangeRow],
) -> tuple[int, int, int, int] | None:
    """取变更生效月集合，扩成前后各 12 个月的查价窗口。"""
    if not rows:
        return None
    keys = sorted({_ym_key(row.effective_year, row.effective_month) for row in rows})
    start_key = max(keys[0] - _PRICE_LOOKBACK_MONTHS, _ym_key(2000, 1))
    end_key = keys[-1] + _PRICE_LOOKBACK_MONTHS
    start_year, start_month = _from_ym_key(start_key)
    end_year, end_month = _from_ym_key(end_key)
    return start_year, start_month, end_year, end_month


def build_engineering_change_summary(
    rows: list[EngineeringChangeRow],
    *,
    sample_limit: int = _SAMPLE_LIMIT,
) -> SummaryPayload:
    if not rows:
        return {
            "subject": "engineering_change",
            "row_count": 0,
            "part_count": 0,
            "change_type_counts": {},
            "change_type_by_level": {},
            "stop_count": 0,
            "not_install_count": 0,
            "discontinue_count": 0,
            "stop_assembly_count": 0,
            "locations": [],
            "vehicle_models": [],
            "items": [],
            "stop_items": [],
            "not_install_items": [],
        }
    part_numbers = {_affected_part_number(row) for row in rows if _affected_part_number(row)}
    change_type_counts = Counter(row.change_type for row in rows)
    by_level: dict[str, dict[str, int]] = {}
    for row in rows:
        level = (row.part_level or "未知").strip() or "未知"
        level_counts = by_level.setdefault(level, {})
        level_counts[row.change_type] = level_counts.get(row.change_type, 0) + 1
    stop_rows = [row for row in rows if row.change_type == CHANGE_TYPE_STOP]
    not_install_rows = [row for row in rows if row.change_type == CHANGE_TYPE_NOT_INSTALL]
    stop_assemblies = {
        (row.before_assembly_part_number or "").strip()
        for row in stop_rows
        if (row.before_assembly_part_number or "").strip()
    }
    return {
        "subject": "engineering_change",
        "row_count": len(rows),
        "part_count": len(part_numbers),
        "change_type_counts": dict(sorted(change_type_counts.items())),
        "change_type_by_level": {
            level: dict(sorted(counts.items())) for level, counts in sorted(by_level.items())
        },
        "stop_count": len(stop_rows),
        "not_install_count": len(not_install_rows),
        "discontinue_count": len(stop_rows) + len(not_install_rows),
        "stop_assembly_count": len(stop_assemblies),
        "locations": sorted({row.location for row in rows}),
        "vehicle_models": sorted({row.vehicle_model for row in rows}),
        "effective_periods": sorted(
            {f"{row.effective_year}-{row.effective_month:02d}" for row in rows}
        ),
        "items": [_item_from_row(row) for row in rows[:sample_limit]],
        "stop_items": [_item_from_row(row) for row in stop_rows[:sample_limit]],
        "not_install_items": [_item_from_row(row) for row in not_install_rows[:sample_limit]],
        "sample_truncated": len(rows) > sample_limit,
    }


def build_engineering_change_drilldown(
    rows: list[EngineeringChangeRow],
    *,
    part_token: str,
    head: EngineeringChangeRow | None = None,
) -> DrilldownPayload:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的工程变更记录",
            "query_token": part_token,
            "before_part_number": None,
            "after_part_number": None,
            "items": [],
        }
    best = head or rows[0]
    return {
        "kind": "drilldown",
        "found": True,
        "query_token": part_token,
        "change_type": best.change_type,
        "before_part_number": best.before_part_number,
        "after_part_number": best.after_part_number,
        "part_name": best.part_name,
        "before_assembly_part_number": best.before_assembly_part_number,
        "after_assembly_part_number": best.after_assembly_part_number,
        "assembly_name": best.assembly_name,
        "part_level": best.part_level,
        "location": best.location,
        "vehicle_model": best.vehicle_model,
        "project_code": best.project_code,
        "effective_year": best.effective_year,
        "effective_month": best.effective_month,
        "is_stop": best.change_type == CHANGE_TYPE_STOP,
        "is_not_install": best.change_type == CHANGE_TYPE_NOT_INSTALL,
        # 口语「变更前叫什么」优先读这两个字段
        "alias_before": best.before_part_number or best.before_assembly_part_number,
        "alias_after": best.after_part_number or best.after_assembly_part_number,
        "items": [_item_from_row(row) for row in rows[:_SAMPLE_LIMIT]],
        "match_count": len(rows),
    }


def build_engineering_change_risks(summary: Mapping[str, object]) -> RiskPayload:
    risks: list[RiskEntry] = []
    stop_count = int(str(summary.get("stop_count") or 0))
    not_install_count = int(str(summary.get("not_install_count") or 0))
    if stop_count:
        risks.append(
            {
                "risk_type": "engineering_change_stop",
                "count": stop_count,
                "message": "有完成停止（整总成不再交货）",
                "samples": _as_object_list(summary.get("stop_items"))[:8],
            }
        )
    if not_install_count:
        risks.append(
            {
                "risk_type": "engineering_change_not_install",
                "count": not_install_count,
                "message": "有此件不装（总成还交、少装零件）",
                "samples": _as_object_list(summary.get("not_install_items"))[:8],
            }
        )
    return {"kind": "risk", "risks": risks}


def _ec_after_part_token(row: EngineeringChangeRow) -> str:
    return (row.after_part_number or "").strip() or (row.after_assembly_part_number or "").strip()


def build_ec_procurement_supplier_status(
    rows: list[EngineeringChangeRow],
    procurement_rows: Sequence[ProcurementObjectRow],
    *,
    sample_limit: int = 20,
    prefer_add_part: bool = False,
) -> SummaryPayload:
    """设变变更后号 ∩ 采购对象：供应商指定四类。

    只看「增加零件 / 改图」的变更后零件号（无零件号再用变更后总成号）。
    完成停止 / 此件不装不进供应商指定盘点。
    """
    if prefer_add_part:
        scoped = [row for row in rows if row.change_type == CHANGE_TYPE_ADD_PART]
    else:
        scoped = [
            row for row in rows if row.change_type in (CHANGE_TYPE_ADD_PART, CHANGE_TYPE_REVISE)
        ]
    procurement_by_part: dict[str, ProcurementObjectRow] = {}
    for prow in procurement_rows:
        key = normalize_part_number_token(prow.part_number)
        if key and key in procurement_by_part:
            continue
        if key:
            procurement_by_part[key] = prow

    with_supplier: list[dict[str, object]] = []
    missing_supplier: list[dict[str, object]] = []
    pending_confirm: list[dict[str, object]] = []
    not_in_procurement: list[dict[str, object]] = []
    seen: set[str] = set()

    for row in scoped:
        token = _ec_after_part_token(row)
        if not token:
            continue
        key = normalize_part_number_token(token)
        if not key or key in seen:
            continue
        seen.add(key)
        base: dict[str, object] = {
            "part_number": token,
            "part_name": row.part_name or row.assembly_name,
            "change_type": row.change_type,
            "location": row.location,
            "vehicle_model": row.vehicle_model,
            "effective_month": month_key(row.effective_year, row.effective_month),
        }
        procurement_row = procurement_by_part.get(key)
        if procurement_row is None:
            not_in_procurement.append(base)
            continue
        entry: dict[str, object] = {
            **base,
            "confirm_status": procurement_row.confirm_status,
            "supplier_name": procurement_row.supplier_name,
            "bom_version": procurement_row.bom_version,
        }
        if (
            procurement_row.confirm_status == "outsourced"
            and not (procurement_row.supplier_name or "").strip()
        ):
            missing_supplier.append(entry)
        elif procurement_row.confirm_status == "pending":
            pending_confirm.append(entry)
        elif (
            procurement_row.supplier_name or ""
        ).strip() or procurement_row.confirm_status == "in_house":
            with_supplier.append(entry)
        else:
            pending_confirm.append(entry)

    return {
        "kind": "ec_procurement_supplier",
        "subject": "engineering_change",
        "purpose": "设变件进采购对象后的供应商指定情况",
        "ec_part_count": len(seen),
        "with_supplier_count": len(with_supplier),
        "missing_supplier_count": len(missing_supplier),
        "pending_confirm_count": len(pending_confirm),
        "not_in_procurement_count": len(not_in_procurement),
        "with_supplier_items": with_supplier[:sample_limit],
        "missing_supplier_items": missing_supplier[:sample_limit],
        "pending_confirm_items": pending_confirm[:sample_limit],
        "not_in_procurement_items": not_in_procurement[:sample_limit],
        "sample_truncated": any(
            len(bucket) > sample_limit
            for bucket in (with_supplier, missing_supplier, pending_confirm, not_in_procurement)
        ),
        "message": (
            f"设变后号 {len(seen)} 个：已指定/自制 {len(with_supplier)}，"
            f"外发缺供应商 {len(missing_supplier)}，待确认 {len(pending_confirm)}，"
            f"未进采购对象 {len(not_in_procurement)}"
        ),
    }


def build_not_install_assembly_impact(
    rows: list[EngineeringChangeRow],
    *,
    assembly_by_part: Mapping[str, Sequence[L0PartPeriodRow]],
    stamping_by_part: Mapping[str, Sequence[StampingPartPeriodRow]],
    sample_limit: int = _SAMPLE_LIMIT,
) -> SummaryPayload:
    """此件不装：少装零件价 vs 所属总成最近卡，估算对总成月账影响。"""
    items: list[dict[str, object]] = []
    for row in rows:
        if row.change_type != CHANGE_TYPE_NOT_INSTALL:
            continue
        part_no = (row.before_part_number or "").strip() or None
        asm_no = (
            (row.after_assembly_part_number or "").strip()
            or (row.before_assembly_part_number or "").strip()
            or None
        )
        part_side = _pick_side(
            part_number=part_no,
            prefer="before",
            effective_year=row.effective_year,
            effective_month=row.effective_month,
            assembly_by_part=assembly_by_part,
            stamping_by_part=stamping_by_part,
        )
        asm_side = _pick_side(
            part_number=asm_no,
            prefer="before",
            effective_year=row.effective_year,
            effective_month=row.effective_month,
            assembly_by_part=assembly_by_part,
            stamping_by_part=stamping_by_part,
        )
        impact: str | None = None
        if part_side is not None:
            impact = money_str(Decimal(str(part_side["unit_price"])))
        items.append(
            {
                "part_number": part_no,
                "part_name": row.part_name,
                "assembly_part_number": asm_no,
                "assembly_name": row.assembly_name,
                "part_unit_price": part_side["unit_price"] if part_side else None,
                "assembly_unit_price": asm_side["unit_price"] if asm_side else None,
                "estimated_assembly_impact": impact,
                "effective_month": month_key(row.effective_year, row.effective_month),
                "note": (
                    "估算：少装该零件的单价；实际总成月账还受用量与其他构成影响"
                    if impact
                    else "未找到少装零件核价卡"
                ),
            }
        )
        if len(items) >= sample_limit:
            break
    return {
        "kind": "not_install_assembly_impact",
        "subject": "engineering_change",
        "purpose": "此件不装对所属总成月账的估算影响",
        "row_count": len(items),
        "items": items,
        "message": (
            f"此件不装 {len(items)} 条，已估少装零件单价影响" if items else "当前范围无此件不装记录"
        ),
    }
