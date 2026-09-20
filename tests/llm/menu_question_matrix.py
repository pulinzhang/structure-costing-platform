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
        "complete",
    ),
    MenuQuestionCase(
        "base-price-download",
        "基准价格列表",
        "基准价",
        "steel_base_price",
        "complete",
    ),
    MenuQuestionCase(
        "winning-thickness-download",
        "中标钢厂厚度价格一览表",
        "中标厚度价",
        "winning_thickness",
        "complete",
    ),
    MenuQuestionCase(
        "scrap-price",
        "废料月度销售价",
        "废料销售价",
        "scrap_price",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-parts",
        "冲压零件列表",
        "冲压工艺",
        "stamping_process",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-tonnage",
        "冲次单价列表",
        "冲次单价",
        "stamping_tonnage",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-process-fee",
        "冲压加工费列表",
        "冲压加工费",
        "stamping_process_fee",
        "complete",
    ),
    MenuQuestionCase(
        "bom-welding-unit-price",
        "焊接单价列表",
        "焊接单价",
        "welding_unit_price",
        "complete",
    ),
    MenuQuestionCase(
        "bom-annual-part-price",
        "年度零件价列表",
        "年度零件价",
        "annual_part_price",
        "complete",
    ),
    MenuQuestionCase(
        "bom-packaging-transport-fee",
        "包装运输费列表",
        "包装运输费",
        "packaging_transport_fee",
        "complete",
    ),
    MenuQuestionCase(
        "bom-material",
        "材料清单列表",
        "材料清单",
        "bom_material",
        "complete",
    ),
    MenuQuestionCase(
        "bom-structure",
        "产品结构",
        "产品结构",
        "bom_material",
        "complete",
    ),
    MenuQuestionCase(
        "bom-viz",
        "产品结构图",
        "结构图",
        "bom_material",
        "complete",
    ),
    MenuQuestionCase(
        "bom-welding-process-breakdown-list",
        "焊接工艺拆解列表",
        "焊接工艺拆解",
        "welding_process_breakdown",
        "complete",
    ),
    MenuQuestionCase(
        "bom-welding-fee-list",
        "成品焊接费列表",
        "成品焊接费",
        "l0_welding_fee",
        "complete",
    ),
    MenuQuestionCase(
        "steel-price-list",
        "冲压钢材联动价一览",
        "钢材联动价",
        "steel_price",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-part-cost",
        "冲压零件价格一览",
        "冲压件成本",
        "stamping_part",
        "complete",
    ),
    MenuQuestionCase(
        "assembly-cost",
        "总成核价一览",
        "成品成本",
        "l0",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-die-fee",
        "冲压模具费列表",
        "模具费",
        "stamping_die_fee",
        "complete",
    ),
    MenuQuestionCase(
        "stamping-gauge-fee",
        "检具费列表",
        "检具费",
        "stamping_gauge_fee",
        "complete",
    ),
    MenuQuestionCase(
        "bom-procurement-object-list",
        "采购对象清单",
        "采购对象清单",
        "procurement_object",
        "complete",
    ),
    MenuQuestionCase(
        "engineering-change-order-list",
        "工程变更单列表",
        "工程变更",
        "engineering_change",
        "complete",
    ),
    MenuQuestionCase(
        "procurement-contract-report",
        "采购价格协议",
        "采购价格",
        None,
        "pending",
    ),
    MenuQuestionCase(
        "costing",
        "自动核价引擎",
        "自动核价",
        None,
        "pending",
    ),
)


def complete_cases() -> list[MenuQuestionCase]:
    return [case for case in MENU_QUESTION_CASES if case.status == "complete"]


def pending_cases() -> list[MenuQuestionCase]:
    return [case for case in MENU_QUESTION_CASES if case.status == "pending"]
