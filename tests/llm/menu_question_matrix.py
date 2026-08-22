# -*- coding: utf-8 -*-
"""侧栏列表页 → 标准问句模板（青岛基地 + 2025年01月 + 主题）。"""

from __future__ import annotations

from dataclasses import dataclass

QUESTION_PREFIX = "青岛基地，2025年01月，"
QUESTION_SUFFIX = "的情况。"


@dataclass(frozen=True, slots=True)
class MenuQuestionCase:
    hash_page: str
    menu_label: str
    question_topic: str
    expected_subject: str | None
    expected_action_id: str | None
    status: str  # complete | pending

    @property
    def user_question(self) -> str:
        return f"{QUESTION_PREFIX}{self.question_topic}{QUESTION_SUFFIX}"


# 与 MENU_COVERAGE 对齐；问句主题选用 QueryParser 可稳定识别的口语
MENU_QUESTION_CASES: tuple[MenuQuestionCase, ...] = (
    MenuQuestionCase(
        "steel-price-policy-download",
        "加减价政策列表",
        "厚度加减价",
        "steel_price_policy",
        "open_steel_price_policy",
        "complete",
    ),
    MenuQuestionCase(
        "base-price-download",
        "基准价格列表",
        "基准价",
        "steel_base_price",
        "open_steel_base_price",
        "complete",
    ),
    MenuQuestionCase(
        "winning-thickness-download",
        "中标钢厂厚度价格一览表",
        "中标厚度价",
        "winning_thickness",
        "open_winning_thickness",
        "complete",
    ),
    MenuQuestionCase(
        "scrap-price",
        "废料月度销售价",
        "废料销售价",
        "scrap_price",
        "open_scrap_price",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-parts",
        "冲压零件列表",
        "冲压工艺",
        "stamping_process",
        "open_stamping_parts",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-tonnage",
        "冲次单价列表",
        "冲次单价",
        "stamping_tonnage",
        "open_stamping_tonnage",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-process-fee",
        "冲压加工费列表",
        "冲压加工费",
        "stamping_process_fee",
        "open_stamping_process_fee",
        "complete",
    ),
    MenuQuestionCase(
        "bom-welding-unit-price",
        "焊接单价列表",
        "焊接单价",
        "welding_unit_price",
        "open_bom_welding_unit_price",
        "complete",
    ),
    MenuQuestionCase(
        "bom-annual-part-price",
        "年度零件价列表",
        "年度零件价",
        "annual_part_price",
        "open_bom_annual_part_price",
        "complete",
    ),
    MenuQuestionCase(
        "bom-packaging-transport-fee",
        "包装运输费列表",
        "包装运输费",
        "packaging_transport_fee",
        "open_bom_packaging_transport_fee",
        "complete",
    ),
    MenuQuestionCase(
        "bom-material",
        "材料清单列表",
        "材料清单",
        "bom_material",
        "open_bom_material",
        "complete",
    ),
    MenuQuestionCase(
        "bom-structure",
        "产品结构",
        "产品结构",
        "bom_material",
        "open_bom_structure",
        "complete",
    ),
    MenuQuestionCase(
        "bom-viz",
        "产品结构图",
        "结构图",
        "bom_material",
        "open_bom_viz",
        "complete",
    ),
    MenuQuestionCase(
        "bom-welding-process-breakdown-list",
        "焊接工艺拆解列表",
        "焊接工艺拆解",
        "welding_process_breakdown",
        "open_bom_welding_process_breakdown_list",
        "complete",
    ),
    MenuQuestionCase(
        "bom-l0-welding-fee-list",
        "成品焊接费列表",
        "成品焊接费",
        "l0_welding_fee",
        "open_bom_l0_welding_fee_list",
        "complete",
    ),
    MenuQuestionCase(
        "steel-price-list",
        "冲压钢材联动价一览",
        "钢材联动价",
        "steel_price",
        "open_steel_price_list",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-part-cost",
        "冲压零件价格一览",
        "冲压件成本",
        "stamping_part",
        "open_stamping_part_cost",
        "complete",
    ),
    MenuQuestionCase(
        "l0-assembly-cost",
        "成品核价一览",
        "成品成本",
        "l0",
        "open_l0_assembly_cost",
        "complete",
    ),
    MenuQuestionCase(
        "costing",
        "自动核价引擎",
        "自动核价",
        None,
        None,
        "pending",
    ),
)


def complete_cases() -> list[MenuQuestionCase]:
    return [case for case in MENU_QUESTION_CASES if case.status == "complete"]


def pending_cases() -> list[MenuQuestionCase]:
    return [case for case in MENU_QUESTION_CASES if case.status == "pending"]
