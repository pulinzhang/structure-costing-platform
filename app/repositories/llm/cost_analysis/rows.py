"""L0 成品核价只读查询的行类型。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class L0MonthlyTotalRow:
    year: int
    month: int
    location: str
    l0_count: int
    ok_count: int
    partial_count: int
    grand_total_sum: Decimal
    total_amount_sum: Decimal
    indirect_amount_sum: Decimal
    stamping_amount_sum: Decimal
    purchased_amount_sum: Decimal
    bundle_amount_sum: Decimal
    welding_amount_sum: Decimal
    welding_other_amount_sum: Decimal
    missing_price_count: int = 0


@dataclass(frozen=True, slots=True)
class L0PartPeriodRow:
    year: int
    month: int
    part_number: str
    part_name: str | None
    grand_total: Decimal
    total_amount: Decimal
    calc_status: str
    missing_leaf_count: int
    calc_message: str | None
    stamping_amount: Decimal
    purchased_amount: Decimal
    bundle_amount: Decimal
    welding_amount: Decimal
    welding_other_fee: Decimal
    indirect_amount: Decimal
    bom_version: str
    should_cost: Decimal | None = None
    level: int = 0
    is_tree_root: bool = True
    object_kind: str | None = None
    location: str | None = None
    vehicle_model: str | None = None
    root_part_number: str | None = None


@dataclass(frozen=True, slots=True)
class LatestAssemblyCardScope:
    year: int
    month: int
    location: str | None
    vehicle_model: str | None
    bom_version: str | None
    part_number: str
    is_tree_root: bool
    object_kind: str | None
    root_part_number: str | None


@dataclass(frozen=True, slots=True)
class AssemblyCardItemRow:
    child_part_number: str
    child_part_name: str | None
    cost_source: str
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal
    supply_type: str | None
    node_level: int


@dataclass(frozen=True, slots=True)
class L0CompositionLineRow:
    """树根核价卡上的一条材料明细（供构成独大分析）。"""

    year: int
    month: int
    root_part_number: str
    root_part_name: str | None
    root_should_cost: Decimal
    child_part_number: str
    child_part_name: str | None
    cost_source: str
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal
    supply_type: str | None = None
    unit: str = "pcs"
    location: str | None = None
