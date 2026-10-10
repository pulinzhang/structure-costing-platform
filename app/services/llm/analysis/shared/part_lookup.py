"""单件跨域存在性：L0 + 冲压价 + 冲压工艺。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.repositories.llm.cost_analysis.rows import L0PartPeriodRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
from app.repositories.llm.stamping_process_analysis_repository import StampingProcessPartRow
from app.schemas.llm.analysis_payload import (
    PartExistencePayload,
    PartPresenceBlock,
    SummaryPayload,
)
from app.services.llm._money import money_str, month_key
from app.services.llm.analysis.shared.drilldown import (
    assembly_card_role,
    pick_finance_card,
)

PartPrimarySource = Literal["l0", "stamping_cost", "stamping_process"]

_L0_DOMAIN_NOTE = (
    "该件为成品供货总成，核价在成品核价一览；"
    "不在冲压零件价格/冲压工艺主数据中单独建账，无记录属正常。"
)
_STAMPING_NA_NOTE = "成品供货总成，无需在冲压零件价格库检索。"
_PROCESS_NA_NOTE = "成品供货总成，无需在冲压工艺主数据检索。"


@dataclass(frozen=True, slots=True)
class PartDataProfile:
    """判定单件落在哪个业务域，避免 L0 成品误报冲压库缺失。"""

    primary_source: PartPrimarySource | None
    stamping_cost_applicable: bool
    stamping_process_applicable: bool
    domain_note: str | None = None


def resolve_part_data_profile(
    *,
    l0_rows: list[L0PartPeriodRow],
    stamping_rows: list[StampingPartPeriodRow],
    process_rows: list[StampingProcessPartRow],
) -> PartDataProfile:
    in_l0 = bool(l0_rows)
    in_stamping = bool(stamping_rows)
    in_process = bool(process_rows)

    supply_assembly = any(row.is_tree_root for row in l0_rows)
    if in_l0 and not in_stamping and not in_process:
        if supply_assembly:
            return PartDataProfile(
                primary_source="l0",
                stamping_cost_applicable=False,
                stamping_process_applicable=False,
                domain_note=_L0_DOMAIN_NOTE,
            )
        return PartDataProfile(
            primary_source="l0",
            stamping_cost_applicable=True,
            stamping_process_applicable=True,
        )
    if in_l0:
        return PartDataProfile(
            primary_source="l0",
            stamping_cost_applicable=in_stamping,
            stamping_process_applicable=in_process,
        )
    if in_stamping:
        return PartDataProfile(
            primary_source="stamping_cost",
            stamping_cost_applicable=True,
            stamping_process_applicable=in_process,
        )
    if in_process:
        return PartDataProfile(
            primary_source="stamping_process",
            stamping_cost_applicable=in_stamping,
            stamping_process_applicable=True,
        )
    return PartDataProfile(
        primary_source=None,
        stamping_cost_applicable=True,
        stamping_process_applicable=True,
    )


def build_part_lookup_summary(
    *,
    query_token: str,
    l0_rows: list[L0PartPeriodRow],
    stamping_rows: list[StampingPartPeriodRow],
    process_rows: list[StampingProcessPartRow],
) -> SummaryPayload:
    resolved: set[str] = set()
    part_names: set[str] = set()
    locations: set[str] = set()

    for l0_row in l0_rows:
        resolved.add(l0_row.part_number)
        if l0_row.part_name:
            part_names.add(l0_row.part_name)
    for stamping_row in stamping_rows:
        resolved.add(stamping_row.part_number)
        if stamping_row.part_name:
            part_names.add(stamping_row.part_name)
        locations.add(stamping_row.stamping_supplier)
    for process_row in process_rows:
        resolved.add(process_row.part_number)
        if process_row.part_name:
            part_names.add(process_row.part_name)
        locations.add(process_row.location)

    return {
        "subject": "part",
        "query_token": query_token,
        "exists_any": bool(l0_rows or stamping_rows or process_rows),
        "resolved_part_numbers": sorted(resolved),
        "part_names": sorted(part_names),
        "locations": sorted(locations),
        "l0_row_count": len(l0_rows),
        "stamping_cost_row_count": len(stamping_rows),
        "stamping_process_count": len(process_rows),
        "in_l0": bool(l0_rows),
        "in_stamping_cost": bool(stamping_rows),
        "in_stamping_process": bool(process_rows),
    }


def _l0_presence(rows: list[L0PartPeriodRow]) -> PartPresenceBlock:
    if not rows:
        return {
            "found": False,
            "source": "l0",
            "message": "成品核价（L0）中未找到该零件号",
            "row_count": 0,
        }
    by_identity: dict[tuple[str, bool, str, int], list[L0PartPeriodRow]] = {}
    for row in rows:
        key = (
            row.part_number,
            bool(row.is_tree_root),
            row.object_kind or "",
            int(row.level or 0),
        )
        by_identity.setdefault(key, []).append(row)
    identities: list[dict[str, object]] = []
    heads: list[L0PartPeriodRow] = []
    for items in by_identity.values():
        latest_item = sorted(items, key=lambda row: (row.year, row.month))[-1]
        heads.append(latest_item)
        identities.append(
            {
                "part_number": latest_item.part_number,
                "part_name": latest_item.part_name,
                "card_role": assembly_card_role(
                    is_tree_root=latest_item.is_tree_root,
                    level=latest_item.level,
                    object_kind=latest_item.object_kind,
                ),
                "is_tree_root": bool(latest_item.is_tree_root),
                "level": int(latest_item.level or 0),
                "object_kind": latest_item.object_kind,
                "root_part_number": latest_item.root_part_number,
                "latest_month": month_key(latest_item.year, latest_item.month),
                "grand_total": money_str(latest_item.grand_total),
                "total_amount": money_str(latest_item.total_amount),
                "location": latest_item.location,
                "vehicle_model": latest_item.vehicle_model,
                "calc_status": latest_item.calc_status,
                "bom_version": latest_item.bom_version,
            }
        )
    latest = pick_finance_card(heads)
    return {
        "found": True,
        "source": "l0",
        "row_count": len(rows),
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
        "latest_month": month_key(latest.year, latest.month),
        "grand_total": money_str(latest.grand_total),
        "total_amount": money_str(latest.total_amount),
        "calc_status": latest.calc_status,
        "bom_version": latest.bom_version,
        "identity_count": len(identities),
        "identities": identities,
    }


def _not_applicable_presence(source: str, note: str) -> PartPresenceBlock:
    return {
        "found": False,
        "source": source,
        "applicable": False,
        "expected_absence": True,
        "row_count": 0,
        "note": note,
    }


def _stamping_cost_presence(
    rows: list[StampingPartPeriodRow],
) -> PartPresenceBlock:
    if not rows:
        return {
            "found": False,
            "source": "stamping_cost",
            "applicable": True,
            "expected_absence": False,
            "message": "冲压零件价格中未找到该零件号",
            "row_count": 0,
        }
    latest = sorted(rows, key=lambda row: (row.year, row.month))[-1]
    return {
        "found": True,
        "source": "stamping_cost",
        "applicable": True,
        "expected_absence": False,
        "row_count": len(rows),
        "part_number": latest.part_number,
        "part_name": latest.part_name,
        "latest_month": month_key(latest.year, latest.month),
        "unit_cost": str(latest.unit_cost),
        "calc_status": latest.calc_status,
        "stamping_supplier": latest.stamping_supplier,
    }


def _stamping_process_presence(
    rows: list[StampingProcessPartRow],
) -> PartPresenceBlock:
    if not rows:
        return {
            "found": False,
            "source": "stamping_process",
            "applicable": True,
            "expected_absence": False,
            "message": "冲压工艺主数据中未找到该零件号",
            "row_count": 0,
        }
    head = rows[0]
    return {
        "found": True,
        "source": "stamping_process",
        "applicable": True,
        "expected_absence": False,
        "row_count": len(rows),
        "part_number": head.part_number,
        "part_name": head.part_name,
        "location": head.location,
        "vehicle_model": head.vehicle_model,
        "version": head.version,
        "process_count": head.process_count,
        "material": head.material,
        "thickness": str(head.thickness) if head.thickness is not None else None,
    }


def build_part_existence(
    *,
    query_token: str,
    l0_rows: list[L0PartPeriodRow],
    stamping_rows: list[StampingPartPeriodRow],
    process_rows: list[StampingProcessPartRow],
) -> PartExistencePayload:
    profile = resolve_part_data_profile(
        l0_rows=l0_rows,
        stamping_rows=stamping_rows,
        process_rows=process_rows,
    )
    l0 = _l0_presence(l0_rows)
    if profile.stamping_cost_applicable:
        stamping_cost = _stamping_cost_presence(stamping_rows)
    else:
        stamping_cost = _not_applicable_presence("stamping_cost", _STAMPING_NA_NOTE)
    if profile.stamping_process_applicable:
        stamping_process = _stamping_process_presence(process_rows)
    else:
        stamping_process = _not_applicable_presence("stamping_process", _PROCESS_NA_NOTE)
    exists_any = l0["found"] or stamping_cost["found"] or stamping_process["found"]
    return {
        "kind": "part_existence",
        "query_token": query_token,
        "primary_source": profile.primary_source,
        "domain_note": profile.domain_note,
        "exists_any": exists_any,
        "l0": l0,
        "stamping_cost": stamping_cost,
        "stamping_process": stamping_process,
    }


def format_part_lookup_message(
    *,
    l0_rows: list[L0PartPeriodRow],
    stamping_rows: list[StampingPartPeriodRow],
    process_rows: list[StampingProcessPartRow],
) -> str:
    if not (l0_rows or stamping_rows or process_rows):
        return "L0、冲压价格、冲压工艺均未命中该零件号"
    profile = resolve_part_data_profile(
        l0_rows=l0_rows,
        stamping_rows=stamping_rows,
        process_rows=process_rows,
    )
    if profile.primary_source == "l0" and profile.domain_note:
        return f"成品核价 供货总成={len(l0_rows)}行"
    if profile.primary_source == "l0" and l0_rows and not any(row.is_tree_root for row in l0_rows):
        return f"成品核价 分总成/子件卡={len(l0_rows)}行"
    parts: list[str] = []
    if l0_rows:
        parts.append(f"L0={len(l0_rows)}行")
    elif profile.primary_source != "l0":
        parts.append("L0=无")
    if stamping_rows:
        parts.append(f"冲压价={len(stamping_rows)}行")
    elif profile.stamping_cost_applicable:
        parts.append("冲压价=无")
    if process_rows:
        parts.append(f"冲压工艺={len(process_rows)}件")
    elif profile.stamping_process_applicable:
        parts.append("冲压工艺=无")
    return "；".join(parts)
