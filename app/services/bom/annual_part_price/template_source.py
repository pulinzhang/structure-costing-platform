"""年度零件价导入模板：基地+项目外购叶子（采购对象 other_leaf ∪ 非工艺库叶子）。"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from app.models.bom.node import BomNode, BomSnapshot
from app.services.bom.annual_part_price.template_builder import AnnualPartPriceTemplateRow

# 与价表设计样例一致：沿用 / 标准件 / 胶块。禁止用采购对象分区名「标准件/胶等」糊整列。
SUPPLY_TYPE_STANDARD = "标准件"
SUPPLY_TYPE_GLUE = "胶块"
SUPPLY_TYPE_CARRYOVER = "沿用"
_GLUE_NAME_KEYS = ("胶",)
_FASTENER_NAME_KEYS = ("螺母", "螺栓", "螺钉", "铆钉", "卡扣", "卡子")


def _normalize_unit(qty_unit: str | None) -> str:
    unit = (qty_unit or "").strip() or "pcs"
    if unit.upper() == "PCS":
        return "pcs"
    return unit


def _has_name_key(part_name: str, keys: tuple[str, ...]) -> bool:
    return any(key in part_name for key in keys)


def resolve_template_supply_type(
    part_name: str,
    *,
    is_other_leaf: bool,
) -> str:
    """原供货类型：胶块 / 标准件 / 沿用（未进工艺库的板料等）。"""
    name = (part_name or "").strip()
    if _has_name_key(name, _GLUE_NAME_KEYS):
        return SUPPLY_TYPE_GLUE
    if is_other_leaf or _has_name_key(name, _FASTENER_NAME_KEYS):
        return SUPPLY_TYPE_STANDARD
    return SUPPLY_TYPE_CARRYOVER


def _make_row(
    *,
    part_number: str,
    part_name: str,
    qty_unit: str | None,
    thickness_text: str | None,
    supply_type: str,
) -> AnnualPartPriceTemplateRow:
    unit = _normalize_unit(qty_unit)
    return AnnualPartPriceTemplateRow(
        part_number=part_number,
        part_name=part_name,
        specification=(thickness_text or "").strip(),
        purchase_unit=unit,
        unit=unit,
        supply_type=supply_type,
    )


def _needs_annual_price(
    part_number: str,
    *,
    child_count: int,
    other_leaf_part_numbers: set[str],
    stamping_part_numbers: set[str],
) -> bool:
    if child_count > 0 or not part_number:
        return False
    if part_number in other_leaf_part_numbers:
        return True
    return part_number not in stamping_part_numbers


def collect_template_rows_from_snapshot_nodes(
    snapshot_nodes: Sequence[tuple[BomSnapshot, Sequence[BomNode]]],
    *,
    other_leaf_part_numbers: set[str],
    stamping_part_numbers: set[str],
) -> list[AnnualPartPriceTemplateRow]:
    """按 snapshot 顺序扫无子件节点；零件号去重（先出现的保留）。"""
    seen_part_numbers: set[str] = set()
    template_rows: list[AnnualPartPriceTemplateRow] = []
    for _snapshot, nodes in snapshot_nodes:
        children_of: dict[int | None, list[BomNode]] = defaultdict(list)
        for node in nodes:
            children_of[node.parent_id].append(node)

        ordered = sorted(
            nodes,
            key=lambda item: (item.excel_row or 0, item.id),
        )
        for node in ordered:
            part_number = (node.part_number or "").strip()
            if not _needs_annual_price(
                part_number,
                child_count=len(children_of.get(node.id, [])),
                other_leaf_part_numbers=other_leaf_part_numbers,
                stamping_part_numbers=stamping_part_numbers,
            ):
                continue
            if part_number in seen_part_numbers:
                continue
            seen_part_numbers.add(part_number)
            part_name = (node.part_name or "").strip()
            template_rows.append(
                _make_row(
                    part_number=part_number,
                    part_name=part_name,
                    qty_unit=node.qty_unit,
                    thickness_text=node.thickness_text,
                    supply_type=resolve_template_supply_type(
                        part_name,
                        is_other_leaf=part_number in other_leaf_part_numbers,
                    ),
                )
            )
    return template_rows
