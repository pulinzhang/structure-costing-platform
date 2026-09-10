"""计算过程页展示标签（不从 export / calc 包引用）。"""

INDIRECT_UNIT_TRANSPORT = "unit_transport_fee"
INDIRECT_WAREHOUSE_BUNDLING = "warehouse_bundling_fee"
INDIRECT_FINANCE = "finished_finance_fee"
INDIRECT_MANAGEMENT = "finished_management_fee"
INDIRECT_SCRAP = "finished_scrap_fee"
INDIRECT_PRETAX_PROFIT = "finished_pretax_profit_fee"
INDIRECT_GAUGE_ALLOC = "gauge_alloc_fee"
INDIRECT_FIXTURE_ALLOC = "fixture_alloc_fee"

COST_SOURCE_LABELS = {
    "stamping": "自制冲压",
    "annual": "外购件",
    "bundle": "一口价",
    "skipped_by_bundle": "已含在一口价",
    "missing": "缺价",
    "sub_assembly": "分总成",
}

DIRECT_INDIRECT_CODES = frozenset({INDIRECT_UNIT_TRANSPORT, INDIRECT_WAREHOUSE_BUNDLING})

INDIRECT_KIND_LABELS = {
    INDIRECT_UNIT_TRANSPORT: "运输费",
    INDIRECT_WAREHOUSE_BUNDLING: "仓储捆包",
    INDIRECT_FINANCE: "资金占用",
    INDIRECT_MANAGEMENT: "管理费",
    INDIRECT_SCRAP: "报废",
    INDIRECT_PRETAX_PROFIT: "利润",
    INDIRECT_GAUGE_ALLOC: "检具分摊",
    INDIRECT_FIXTURE_ALLOC: "工装分摊",
}


DOCUMENT_CATEGORY_LABELS = {
    "stamping_part": "冲压工艺",
    "stamping_process_confirm": "冲压工艺",
    "stamping_process_fee": "冲压加工费",
    "stamping_die": "冲压模具布点",
    "stamping_tonnage_price": "冲次单价",
    "stamping_gauge_fee": "冲压检具费",
    "steel_base_price": "钢价基准价",
    "steel_thickness_policy": "厚度加减价",
    "steel_price_policy": "加减价政策",
    "bom_packaging_transport_fee": "包装运输费",
    "bom_annual_part_price": "年度零件价",
    "bom_welding_unit_price": "焊接单价",
    "bom_material": "BOM 材料清单",
}


def document_category_label(category: str) -> str:
    return DOCUMENT_CATEGORY_LABELS.get(category, "资料")


def cost_source_label(source: str | None) -> str:
    if not source:
        return ""
    return COST_SOURCE_LABELS.get(source, source)


def indirect_kind(code: str) -> str:
    if code in DIRECT_INDIRECT_CODES:
        return "direct"
    return "allocation"
