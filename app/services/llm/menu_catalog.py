"""subject → 侧栏列表页（与 static/index.html 菜单对齐）。"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.llm.analysis_query import AnalysisQuery


@dataclass(frozen=True, slots=True)
class MenuTarget:
    """一个分析主题对应的主列表页。"""

    hash_page: str
    action_id: str
    label: str


@dataclass(frozen=True, slots=True)
class MenuCoverageItem:
    """侧栏列表页覆盖状态（查检用）。"""

    hash_page: str
    menu_label: str
    subject: str | None
    status: str  # complete | pending
    notes: str = ""


# subject → 主 Action 落点
SUBJECT_MENU: dict[str, MenuTarget] = {
    "stamping_process": MenuTarget(
        hash_page="stamping-parts",
        action_id="open_stamping_parts",
        label="打开冲压零件列表",
    ),
    "stamping_part": MenuTarget(
        hash_page="stamping-part-cost",
        action_id="open_stamping_part_cost",
        label="打开冲压零件价格一览",
    ),
    "stamping_tonnage": MenuTarget(
        hash_page="stamping-tonnage",
        action_id="open_stamping_tonnage",
        label="打开冲次单价列表",
    ),
    "stamping_process_fee": MenuTarget(
        hash_page="stamping-process-fee",
        action_id="open_stamping_process_fee",
        label="打开冲压加工费列表",
    ),
    "l0": MenuTarget(
        hash_page="l0-assembly-cost",
        action_id="open_l0_assembly_cost",
        label="打开成品核价一览",
    ),
    "cost_total": MenuTarget(
        hash_page="l0-assembly-cost",
        action_id="open_l0_assembly_cost",
        label="打开成品核价一览",
    ),
    "steel_price": MenuTarget(
        hash_page="steel-price-list",
        action_id="open_steel_price_list",
        label="打开冲压钢材联动价一览",
    ),
    "steel_price_policy": MenuTarget(
        hash_page="steel-price-policy-download",
        action_id="open_steel_price_policy",
        label="打开加减价政策列表",
    ),
    "steel_base_price": MenuTarget(
        hash_page="base-price-download",
        action_id="open_steel_base_price",
        label="打开基准价格列表",
    ),
    "winning_thickness": MenuTarget(
        hash_page="winning-thickness-download",
        action_id="open_winning_thickness",
        label="打开中标钢厂厚度价格一览表",
    ),
    "scrap_price": MenuTarget(
        hash_page="scrap-price",
        action_id="open_scrap_price",
        label="打开废料月度销售价",
    ),
    "welding_unit_price": MenuTarget(
        hash_page="bom-welding-unit-price",
        action_id="open_bom_welding_unit_price",
        label="打开焊接单价列表",
    ),
    "annual_part_price": MenuTarget(
        hash_page="bom-annual-part-price",
        action_id="open_bom_annual_part_price",
        label="打开年度零件价列表",
    ),
    "packaging_transport_fee": MenuTarget(
        hash_page="bom-packaging-transport-fee",
        action_id="open_bom_packaging_transport_fee",
        label="打开包装运输费列表",
    ),
    "bom_material": MenuTarget(
        hash_page="bom-material",
        action_id="open_bom_material",
        label="打开材料清单列表",
    ),
    "welding_process_breakdown": MenuTarget(
        hash_page="bom-welding-process-breakdown-list",
        action_id="open_bom_welding_process_breakdown_list",
        label="打开焊接工艺拆解列表",
    ),
    "l0_welding_fee": MenuTarget(
        hash_page="bom-l0-welding-fee-list",
        action_id="open_bom_l0_welding_fee_list",
        label="打开成品焊接费列表",
    ),
    "part": MenuTarget(
        hash_page="l0-assembly-cost",
        action_id="open_l0_assembly_cost",
        label="打开成品核价一览",
    ),
}

# 侧栏「列表/一览」页覆盖查检（上传/计算页不在此列）
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
        "中标钢厂厚度价格一览表",
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
        "bom-l0-welding-fee-list",
        "成品焊接费列表",
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
        "冲压钢材联动价一览",
        "steel_price",
        "complete",
    ),
    MenuCoverageItem(
        "stamping-part-cost",
        "冲压零件价格一览",
        "stamping_part",
        "complete",
    ),
    MenuCoverageItem(
        "l0-assembly-cost",
        "成品核价一览",
        "l0",
        "complete",
        "cost_total 同落点",
    ),
    MenuCoverageItem(
        "costing",
        "自动核价引擎",
        None,
        "pending",
        "编排页，非标准列表分析",
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
    ("bom-l0-welding-fee-list", "l0_welding_fee"),
    ("steel-price-policy-download", "steel_price_policy"),
    ("base-price-download", "steel_base_price"),
    ("winning-thickness-download", "winning_thickness"),
    ("scrap-price", "scrap_price"),
    ("steel-price-list", "steel_price"),
    ("stamping-part-cost", "stamping_part"),
    ("l0-assembly-cost", "l0"),
)


def resolve_menu_target(query: AnalysisQuery) -> MenuTarget:
    """按 subject 选主落点；零件号 + 冲压语境走工艺或核价一览。"""
    subject = query.subject
    question = query.user_question or ""
    if subject == "part" and "冲压" in question:
        if any(
            word in question
            for word in ("工艺", "工序", "模具", "OP10", "OP20")
        ):
            return SUBJECT_MENU["stamping_process"]
        return SUBJECT_MENU["stamping_part"]
    if subject == "bom_material":
        if "结构图" in question:
            return MenuTarget(
                hash_page="bom-viz",
                action_id="open_bom_viz",
                label="打开产品结构图",
            )
        if any(word in question for word in ("产品结构", "结构树", "BOM结构")):
            return MenuTarget(
                hash_page="bom-structure",
                action_id="open_bom_structure",
                label="打开产品结构",
            )
    return SUBJECT_MENU.get(subject, SUBJECT_MENU["cost_total"])


def expand_base_price_location(location: str) -> str:
    """基准价表用「青岛基地」；核价表用「青岛」。"""
    text = (location or "").strip()
    if not text:
        return ""
    if text.endswith("基地"):
        return text
    return f"{text}基地"


def build_list_params(query: AnalysisQuery) -> dict[str, str]:
    """生成与业务列表页 readHashFilters 一致的 query 参数。"""
    year = str(query.time_range.end_year)
    month = str(query.time_range.end_month)

    if query.subject == "steel_price_policy":
        params: dict[str, str] = {"year": year, "month": month}
        steel_mill = query.filter_get("steel_mill")
        category_name = query.filter_get("category_name")
        if steel_mill:
            params["steel_mill"] = steel_mill
        if category_name:
            params["category_name"] = category_name
        return params

    if query.subject == "steel_base_price":
        params = {"year": year, "month": month}
        location = expand_base_price_location(query.location() or "")
        if location:
            params["location"] = location
        steel_mill = query.filter_get("steel_mill")
        category_name = query.filter_get("category_name")
        grade = query.filter_get("grade")
        if steel_mill:
            params["steel_mill"] = steel_mill
        if category_name:
            params["category_name"] = category_name
        if grade:
            params["grade"] = grade
        return params

    if query.subject == "stamping_process":
        params = {}
        location = query.location() or ""
        vehicle_model = query.vehicle_model() or ""
        version = query.bom_version() or ""
        part_number = query.part_number() or ""
        if location:
            params["location"] = location
        if vehicle_model:
            params["vehicle_model"] = vehicle_model
        if version:
            params["version"] = version
        if part_number:
            params["part_number"] = part_number
        return params

    if query.subject == "stamping_tonnage":
        params = {"year": year}
        location = query.location() or ""
        tonnage = query.tonnage()
        if location:
            params["location"] = location
        if tonnage is not None:
            params["tonnage"] = str(tonnage)
        return params

    if query.subject == "stamping_process_fee":
        params = {"year": year}
        location = query.location() or ""
        vehicle_model = query.vehicle_model() or ""
        version = query.bom_version() or ""
        part_number = query.part_number() or ""
        if location:
            params["location"] = location
        if vehicle_model:
            params["vehicle_model"] = vehicle_model
        if version:
            params["version"] = version
        if part_number:
            params["part_number"] = part_number
        return params

    if query.subject == "winning_thickness":
        params = {"year": year, "month": month}
        location = expand_base_price_location(query.location() or "")
        if location:
            params["location"] = location
        steel_mill = query.filter_get("steel_mill")
        category_name = query.filter_get("category_name")
        grade = query.filter_get("grade")
        if steel_mill:
            params["steel_mill"] = steel_mill
        if category_name:
            params["category_name"] = category_name
        if grade:
            params["grade"] = grade
        return params

    if query.subject == "scrap_price":
        return {"year": year, "month": month}

    if query.subject == "welding_unit_price":
        params = {"year": year}
        location = query.location() or ""
        if location:
            params["location"] = location
        return params

    if query.subject == "annual_part_price":
        params = {"year": year}
        location = query.location() or ""
        part_number = query.part_number() or ""
        if location:
            params["location"] = location
        if part_number:
            params["part_number"] = part_number
        return params

    if query.subject == "packaging_transport_fee":
        params = {"year": year}
        location = query.location() or ""
        vehicle_model = query.vehicle_model() or ""
        part_number = query.part_number() or ""
        if location:
            params["location"] = location
        if vehicle_model:
            params["vehicle_model"] = vehicle_model
        if part_number:
            params["part_number"] = part_number
        return params

    if query.subject == "bom_material":
        params = {}
        location = query.location() or ""
        vehicle_model = query.vehicle_model() or ""
        bom_version = query.bom_version() or ""
        part_number = query.part_number() or ""
        if location:
            params["location"] = location
        if vehicle_model:
            params["vehicle_model"] = vehicle_model
        if bom_version:
            params["bom_version"] = bom_version
        if part_number:
            params["part_number"] = part_number
        return params

    if query.subject == "welding_process_breakdown":
        params = {}
        location = query.location() or ""
        vehicle_model = query.vehicle_model() or ""
        bom_version = query.bom_version() or ""
        part_number = query.part_number() or ""
        if location:
            params["location"] = location
        if vehicle_model:
            params["vehicle_model"] = vehicle_model
        if bom_version:
            params["bom_version"] = bom_version
        if part_number:
            params["part_number"] = part_number
        return params

    if query.subject == "l0_welding_fee":
        params = {"year": year}
        location = query.location() or ""
        vehicle_model = query.vehicle_model() or ""
        bom_version = query.bom_version() or ""
        part_number = query.part_number() or ""
        if location:
            params["location"] = location
        if vehicle_model:
            params["vehicle_model"] = vehicle_model
        if bom_version:
            params["bom_version"] = bom_version
        if part_number:
            params["part_number"] = part_number
        return params

    location = query.location() or ""
    start = query.time_range.start
    end = query.time_range.end
    vehicle_model = query.vehicle_model() or ""
    bom_version = query.bom_version() or ""
    part_number = query.part_number() or ""

    params = {
        "location": location,
        "year": year,
        "month": month,
        "vehicle_model": vehicle_model,
        "bom_version": bom_version,
        "start": start,
        "end": end,
    }
    if part_number:
        params["part_number"] = part_number
    return params


_PAGE_PARAM_SUBJECT: dict[str, str] = {
    "stamping-parts": "stamping_process",
    "stamping-part-cost": "stamping_part",
    "stamping-process-fee": "stamping_process_fee",
    "bom-material": "bom_material",
    "bom-structure": "bom_material",
    "bom-viz": "bom_material",
    "bom-welding-process-breakdown-list": "welding_process_breakdown",
    "bom-l0-welding-fee-list": "l0_welding_fee",
    "l0-assembly-cost": "l0",
}


def build_list_params_for_page(query: AnalysisQuery, hash_page: str) -> dict[str, str]:
    """按目标列表页生成深链参数（单件跨域检索时用）。"""
    override = _PAGE_PARAM_SUBJECT.get(hash_page)
    if override and override != query.subject:
        query = query.model_copy(update={"subject": override})
    return build_list_params(query)
