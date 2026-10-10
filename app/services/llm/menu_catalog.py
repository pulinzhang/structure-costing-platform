"""subject → 侧栏列表页（与 static/index.html 菜单对齐）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MenuTarget:
    """一个分析主题对应的主列表页。"""

    hash_page: str
    label: str


@dataclass(frozen=True, slots=True)
class MenuCoverageItem:
    """侧栏列表页覆盖状态（查检用）。"""

    hash_page: str
    menu_label: str
    subject: str | None
    status: str  # complete | pending
    notes: str = ""


# subject → 主列表页落点
SUBJECT_MENU: dict[str, MenuTarget] = {
    "stamping_process": MenuTarget(
        hash_page="stamping-parts",
        label="打开冲压零件列表",
    ),
    "stamping_part": MenuTarget(
        hash_page="stamping-part-cost",
        label="打开冲压零件价格列表",
    ),
    "stamping_tonnage": MenuTarget(
        hash_page="stamping-tonnage",
        label="打开冲次单价列表",
    ),
    "stamping_process_fee": MenuTarget(
        hash_page="stamping-process-fee",
        label="打开冲压加工费列表",
    ),
    "l0": MenuTarget(
        hash_page="assembly-cost",
        label="打开总成核价列表",
    ),
    "cost_total": MenuTarget(
        hash_page="assembly-cost",
        label="打开总成核价列表",
    ),
    "steel_price": MenuTarget(
        hash_page="steel-price-list",
        label="打开冲压钢材联动价列表",
    ),
    "steel_price_policy": MenuTarget(
        hash_page="steel-price-policy-download",
        label="打开加减价政策列表",
    ),
    "steel_base_price": MenuTarget(
        hash_page="base-price-download",
        label="打开基准价格列表",
    ),
    "winning_thickness": MenuTarget(
        hash_page="winning-thickness-download",
        label="打开中标钢厂厚度价格列表",
    ),
    "scrap_price": MenuTarget(
        hash_page="scrap-price",
        label="打开废料月度销售价",
    ),
    "welding_unit_price": MenuTarget(
        hash_page="bom-welding-unit-price",
        label="打开焊接单价列表",
    ),
    "annual_part_price": MenuTarget(
        hash_page="bom-annual-part-price",
        label="打开年度零件价列表",
    ),
    "packaging_transport_fee": MenuTarget(
        hash_page="bom-packaging-transport-fee",
        label="打开包装运输费列表",
    ),
    "bom_material": MenuTarget(
        hash_page="bom-material",
        label="打开材料清单列表",
    ),
    "welding_process_breakdown": MenuTarget(
        hash_page="bom-welding-process-breakdown-list",
        label="打开焊接工艺拆解列表",
    ),
    "l0_welding_fee": MenuTarget(
        hash_page="bom-welding-fee-list",
        label="打开焊接费列表",
    ),
    "part": MenuTarget(
        hash_page="assembly-cost",
        label="打开总成核价列表",
    ),
    "ops_workbench": MenuTarget(
        hash_page="assembly-cost",
        label="打开总成核价列表",
    ),
    "stamping_die_fee": MenuTarget(
        hash_page="stamping-die-fee",
        label="打开冲压模具费列表",
    ),
    "stamping_gauge_fee": MenuTarget(
        hash_page="stamping-gauge-fee",
        label="打开检具费列表",
    ),
    "procurement_object": MenuTarget(
        hash_page="bom-procurement-object-list",
        label="打开采购对象列表",
    ),
    "engineering_change": MenuTarget(
        hash_page="engineering-change-order-list",
        label="打开设计变更列表",
    ),
}

# 侧栏列表页覆盖查检（上传/计算页不在此列）
MENU_COVERAGE: tuple[MenuCoverageItem, ...] = (
    # 一事一议
    MenuCoverageItem(
        "steel-price-policy-download",
        "加减价政策列表",
        "steel_price_policy",
        "complete",
    ),
    MenuCoverageItem(
        "base-price-download",
        "基准价格列表",
        "steel_base_price",
        "complete",
    ),
    MenuCoverageItem(
        "winning-thickness-download",
        "中标钢厂厚度价格列表",
        "winning_thickness",
        "complete",
    ),
    MenuCoverageItem(
        "scrap-price",
        "废料月度销售价",
        "scrap_price",
        "complete",
    ),
    # 焊接工程
    MenuCoverageItem(
        "bom-welding-unit-price",
        "焊接单价列表",
        "welding_unit_price",
        "complete",
    ),
    MenuCoverageItem(
        "bom-annual-part-price",
        "年度零件价列表",
        "annual_part_price",
        "complete",
        "口语「一口价」同落点",
    ),
    MenuCoverageItem(
        "bom-packaging-transport-fee",
        "包装运输费列表",
        "packaging_transport_fee",
        "complete",
    ),
    MenuCoverageItem(
        "bom-material",
        "材料清单列表",
        "bom_material",
        "complete",
    ),
    MenuCoverageItem(
        "bom-structure",
        "产品结构",
        "bom_material",
        "complete",
        "同材料清单数据",
    ),
    MenuCoverageItem(
        "bom-viz",
        "产品结构图",
        "bom_material",
        "complete",
        "同材料清单数据",
    ),
    MenuCoverageItem(
        "bom-welding-process-breakdown-list",
        "焊接工艺拆解列表",
        "welding_process_breakdown",
        "complete",
    ),
    MenuCoverageItem(
        "bom-welding-fee-list",
        "焊接费列表",
        "l0_welding_fee",
        "complete",
    ),
    # 冲压工程
    MenuCoverageItem(
        "stamping-parts",
        "冲压零件列表",
        "stamping_process",
        "complete",
        "冲压工艺主数据",
    ),
    MenuCoverageItem(
        "stamping-tonnage",
        "冲次单价列表",
        "stamping_tonnage",
        "complete",
    ),
    MenuCoverageItem(
        "stamping-process-fee",
        "冲压加工费列表",
        "stamping_process_fee",
        "complete",
    ),
    # 核价
    MenuCoverageItem(
        "steel-price-list",
        "冲压钢材联动价列表",
        "steel_price",
        "complete",
    ),
    MenuCoverageItem(
        "stamping-part-cost",
        "冲压零件价格列表",
        "stamping_part",
        "complete",
    ),
    MenuCoverageItem(
        "assembly-cost",
        "总成核价列表",
        "l0",
        "complete",
        "cost_total 同落点",
    ),
    MenuCoverageItem(
        "stamping-die-fee",
        "冲压模具费列表",
        "stamping_die_fee",
        "complete",
    ),
    MenuCoverageItem(
        "stamping-gauge-fee",
        "检具费列表",
        "stamping_gauge_fee",
        "complete",
    ),
    MenuCoverageItem(
        "bom-procurement-object-list",
        "采购对象列表",
        "procurement_object",
        "complete",
    ),
    MenuCoverageItem(
        "engineering-change-order-list",
        "设计变更列表",
        "engineering_change",
        "complete",
    ),
    MenuCoverageItem(
        "costing",
        "自动核价引擎",
        None,
        "pending",
        "编排页，非标准列表分析",
    ),
    # 采购价格协议（一级叶子，不在核价组）
    MenuCoverageItem(
        "procurement-contract-report",
        "采购价格协议",
        None,
        "pending",
        "查询+导出页，非标准列表分析",
    ),
)

# 实体表列表页 → subject（排除上传/计算/仪表盘/报价/设置）
ENTITY_LIST_PAGES: tuple[tuple[str, str], ...] = (
    ("stamping-parts", "stamping_process"),
    ("stamping-tonnage", "stamping_tonnage"),
    ("stamping-process-fee", "stamping_process_fee"),
    ("bom-material", "bom_material"),
    ("bom-structure", "bom_material"),
    ("bom-viz", "bom_material"),
    ("bom-welding-unit-price", "welding_unit_price"),
    ("bom-annual-part-price", "annual_part_price"),
    ("bom-packaging-transport-fee", "packaging_transport_fee"),
    ("bom-welding-process-breakdown-list", "welding_process_breakdown"),
    ("bom-welding-fee-list", "l0_welding_fee"),
    ("steel-price-policy-download", "steel_price_policy"),
    ("base-price-download", "steel_base_price"),
    ("winning-thickness-download", "winning_thickness"),
    ("scrap-price", "scrap_price"),
    ("steel-price-list", "steel_price"),
    ("stamping-part-cost", "stamping_part"),
    ("assembly-cost", "l0"),
    ("stamping-die-fee", "stamping_die_fee"),
    ("stamping-gauge-fee", "stamping_gauge_fee"),
    ("bom-procurement-object-list", "procurement_object"),
    ("engineering-change-order-list", "engineering_change"),
)
