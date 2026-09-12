"""成品月核价写入载荷与列表汇总形状。

改落库字段：这里的 dataclass + MAIN_FIELDS 必须和 Model 列一起改。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, TypedDict

from app.models.costing.assembly_cost import AssemblyCost

SettlementAmountField = Literal["total_amount", "grand_total"]
_SETTLEMENT_AMOUNT_COLUMNS = {
    "total_amount": AssemblyCost.total_amount,
    "grand_total": AssemblyCost.grand_total,
}
_IN_CHUNK = 400


def _chunks(values: list[int]) -> list[list[int]]:
    if not values:
        return []
    return [values[index : index + _IN_CHUNK] for index in range(0, len(values), _IN_CHUNK)]


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class AssemblyCostItemInsert:
    node_level: int
    bom_node_id: int | None
    part_number: str
    part_name: str | None
    node_role: str | None
    supply_type: str | None
    cost_source: str
    match_hint: str | None
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal
    sort_no: int


@dataclass(frozen=True)
class AssemblyCostIndirectInsert:
    code: str
    label: str
    amount: Decimal
    rate: Decimal | None
    base_amount: Decimal | None
    sort_no: int


@dataclass
class AssemblyCostUpsertPayload:
    year: int
    month: int
    location: str
    vehicle_model: str
    bom_version: str
    source_node_id: int
    level: int
    is_tree_root: bool
    parent_node_id: int | None
    root_part_number: str | None
    root_part_name: str | None
    procurement_object_id: int | None
    object_kind: str | None
    part_number: str
    part_name: str | None
    supply_qty: Decimal
    bom_snapshot_id: int | None
    sketch_url: str | None
    stamping_amount: Decimal
    purchased_amount: Decimal
    bundle_amount: Decimal
    material_amount: Decimal
    welding_amount: Decimal
    welding_other_fee: Decimal
    total_amount: Decimal
    should_cost: Decimal
    vendor_quote: Decimal | None
    gap_amount: Decimal | None
    vendor_name: str | None
    unit_transport_fee: Decimal
    warehouse_bundling_fee: Decimal
    finished_finance_fee: Decimal
    finished_management_fee: Decimal
    finished_scrap_fee: Decimal
    finished_pretax_profit_fee: Decimal
    gauge_alloc_fee: Decimal
    fixture_alloc_fee: Decimal
    allocation_fee_total: Decimal
    indirect_amount: Decimal
    grand_total: Decimal
    finance_rate: Decimal
    management_rate: Decimal
    scrap_rate: Decimal
    pretax_profit_rate: Decimal
    welding_fee_id: int | None
    welding_summary: str | None
    calc_status: str
    missing_leaf_count: int
    calc_message: str | None
    formula_version: str | None
    calculated_at: datetime | None
    calc_batch_id: str | None
    created_by: str
    updated_by: str
    items: list[AssemblyCostItemInsert]
    indirects: list[AssemblyCostIndirectInsert]


class AssemblyCostFilterSummary(TypedDict):
    """列表 HUD 汇总（全量筛选，非本页）。`total_amount_sum` 是月总账，看板不展示。"""

    total_count: int
    ok_count: int
    partial_count: int
    pending_count: int
    approved_count: int
    grand_total_sum: Decimal
    total_amount_sum: Decimal
    avg_grand_total: Decimal | None
    material_amount_sum: Decimal
    welding_amount_sum: Decimal


def empty_assembly_cost_summary() -> AssemblyCostFilterSummary:
    return {
        "total_count": 0,
        "ok_count": 0,
        "partial_count": 0,
        "pending_count": 0,
        "approved_count": 0,
        "grand_total_sum": Decimal("0"),
        "total_amount_sum": Decimal("0"),
        "avg_grand_total": None,
        "material_amount_sum": Decimal("0"),
        "welding_amount_sum": Decimal("0"),
    }


class AssemblyCostListFilters(TypedDict):
    year: int | None
    month: int | None
    location: str | None
    vehicle_model: str | None
    bom_version: str | None
    part_number: str | None
    audit_status: str | None
    calc_status: str | None
    view: str
    level: int | None
    object_kind: str | None
    summary: AssemblyCostFilterSummary


_MAIN_FIELDS = (
    "source_node_id",
    "level",
    "is_tree_root",
    "parent_node_id",
    "root_part_number",
    "root_part_name",
    "procurement_object_id",
    "object_kind",
    "part_number",
    "part_name",
    "supply_qty",
    "bom_snapshot_id",
    "sketch_url",
    "stamping_amount",
    "purchased_amount",
    "bundle_amount",
    "material_amount",
    "welding_amount",
    "welding_other_fee",
    "total_amount",
    "should_cost",
    "vendor_quote",
    "gap_amount",
    "vendor_name",
    "unit_transport_fee",
    "warehouse_bundling_fee",
    "finished_finance_fee",
    "finished_management_fee",
    "finished_scrap_fee",
    "finished_pretax_profit_fee",
    "gauge_alloc_fee",
    "fixture_alloc_fee",
    "allocation_fee_total",
    "indirect_amount",
    "grand_total",
    "finance_rate",
    "management_rate",
    "scrap_rate",
    "pretax_profit_rate",
    "welding_fee_id",
    "welding_summary",
    "calc_status",
    "missing_leaf_count",
    "calc_message",
    "formula_version",
    "calculated_at",
    "calc_batch_id",
    "updated_by",
)
