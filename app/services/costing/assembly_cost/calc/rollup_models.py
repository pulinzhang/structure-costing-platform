"""总成月核价 rollup：公式版本、间接费代码与数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

FORMULA_VERSION = "assembly-v1"

CostSource = Literal["stamping", "annual", "bundle", "skipped_by_bundle", "missing"]
CalcStatus = Literal["ok", "partial"]

INDIRECT_UNIT_TRANSPORT = "unit_transport_fee"
INDIRECT_WAREHOUSE_BUNDLING = "warehouse_bundling_fee"
INDIRECT_FINANCE = "finished_finance_fee"
INDIRECT_MANAGEMENT = "finished_management_fee"
INDIRECT_SCRAP = "finished_scrap_fee"
INDIRECT_PRETAX_PROFIT = "finished_pretax_profit_fee"
INDIRECT_GAUGE_ALLOC = "gauge_alloc_fee"
INDIRECT_FIXTURE_ALLOC = "fixture_alloc_fee"

INDIRECT_LABELS: dict[str, str] = {
    INDIRECT_UNIT_TRANSPORT: "单件运输费",
    INDIRECT_WAREHOUSE_BUNDLING: "仓储费+捆包费",
    INDIRECT_FINANCE: "财务费",
    INDIRECT_MANAGEMENT: "管理费",
    INDIRECT_SCRAP: "报废费用",
    INDIRECT_PRETAX_PROFIT: "税前利润",
    INDIRECT_GAUGE_ALLOC: "检具分摊费",
    INDIRECT_FIXTURE_ALLOC: "器具分摊费",
}


@dataclass(frozen=True)
class RollupBomNode:
    id: int
    parent_id: int | None
    level: int
    part_number: str
    part_name: str | None
    qty: Decimal
    node_role: str
    sort_no: int = 0
    seq_no: int | None = None
    excel_row: int | None = None
    supply_type: str | None = None
    sketch_url: str | None = None
    snapshot_id: int | None = None
    bom_version: str = ""


@dataclass(frozen=True)
class RollupWeldingFee:
    final_amount: Decimal
    other_fee: Decimal = Decimal("0")
    missing_price_count: int = 0
    welding_fee_id: int | None = None
    summary: str | None = None
    calc_status: str | None = None


@dataclass(frozen=True)
class RollupPackagingFee:
    unit_transport_fee: Decimal = Decimal("0")
    warehouse_bundling_fee: Decimal = Decimal("0")


@dataclass(frozen=True)
class RollupFinishedRates:
    finance_rate: Decimal
    management_rate: Decimal
    scrap_rate: Decimal
    pretax_profit_rate: Decimal


@dataclass(frozen=True)
class RollupAllocationFees:
    """检具/器具分摊（上游未建时为 0，仍计入 grand_total）。"""

    gauge_alloc_fee: Decimal = Decimal("0")
    fixture_alloc_fee: Decimal = Decimal("0")


@dataclass(frozen=True)
class RollupLine:
    node_level: int
    bom_node_id: int | None
    part_number: str
    part_name: str | None
    node_role: str | None
    supply_type: str | None
    cost_source: CostSource
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal
    match_hint: str | None = None
    sort_no: int = 0


@dataclass(frozen=True)
class RollupIndirectLine:
    code: str
    label: str
    amount: Decimal
    rate: Decimal | None = None
    base_amount: Decimal | None = None
    sort_no: int = 0


@dataclass
class RollupResult:
    part_number: str
    part_name: str | None
    supply_qty: Decimal
    sketch_url: str | None
    status: CalcStatus
    stamping_amount: Decimal
    purchased_amount: Decimal
    bundle_amount: Decimal
    material_amount: Decimal
    welding_amount: Decimal
    welding_other_fee: Decimal
    total_amount: Decimal
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
    missing_leaf_count: int
    should_cost: Decimal = Decimal("0")
    vendor_quote: Decimal | None = None
    gap_amount: Decimal | None = None
    vendor_name: str | None = None
    source_node_id: int | None = None
    level: int = 0
    is_tree_root: bool = False
    parent_node_id: int | None = None
    root_part_number: str | None = None
    root_part_name: str | None = None
    identities_ok: bool = True
    lines: list[RollupLine] = field(default_factory=list)
    indirect_lines: list[RollupIndirectLine] = field(default_factory=list)
    formula_version: str = FORMULA_VERSION
