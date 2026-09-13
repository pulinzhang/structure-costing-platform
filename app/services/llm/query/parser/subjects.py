"""口语 → subject。顺序即优先级，加新实体只改本文件。"""

from __future__ import annotations

from app.schemas.llm.analysis_query import AnalysisKind
from app.services.llm.query.parser.part_price import (
    is_drilldown_focused,
    is_standard_part_price_question,
)

# 口语「中标价」= 基准价格列表（#/base-price-download），不是「中标厚度价格一览」
_BASE_PRICE_TERMS: tuple[str, ...] = (
    "基准价",
    "基准价格",
    "到厂价",
    "原卷承兑",
    "中标价",
)
_WINNING_THICKNESS_TERMS: tuple[str, ...] = (
    "中标厚度价",
    "中标厚度",
    "中标钢厂厚度",
    "厚度价格一览",
    "厚度价格一览表",
)
_POLICY_TERMS: tuple[str, ...] = (
    "加减价",
    "加减价政策",
    "厚度加减",
    "厚度加减价",
    "厚度政策",
    "宽度加价",
    "宽度加减",
    "宽度政策",
    "锌层加减",
    "锌层加价",
)


def is_stamping_costing_question(question: str) -> bool:
    if any(
        word in question
        for word in ("冲压工艺", "工艺路线", "工艺文件", "冲次单价", "冲次价格", "冲次价", "冲次")
    ):
        return False
    if any(
        word in question
        for word in ("冲压核价", "冲压零件核价", "冲压零件价格", "冲压件成本", "冲压零件价")
    ):
        return True
    return "冲压" in question and any(
        word in question for word in ("核价", "成本", "价格", "零件价")
    )


def is_welding_fee_question(question: str) -> bool:
    if "焊接单价" in question:
        return False
    if "焊接工艺拆解" in question or ("工艺拆解" in question and "焊接" in question):
        return False
    return any(
        word in question
        for word in ("焊接成本", "焊接费", "焊接核价", "焊接成本计算", "成品焊接费")
    )


def is_gauge_fee_question(question: str) -> bool:
    return "检具费" in question


def is_die_fee_question(question: str) -> bool:
    if is_gauge_fee_question(question):
        return False
    return "模具费" in question


def is_procurement_object_question(question: str) -> bool:
    if any(word in question for word in ("采购价格协议", "批量零部件价格协议", "导出协议")):
        return False
    if "采购对象" in question:
        return True
    return any(word in question for word in ("还没确认外发", "待确认外发", "外发确认", "确认外发"))


def is_ops_workbench_question(question: str) -> bool:
    if any(word in question for word in ("异常", "单价为0", "单价是0", "偏差", "多少钱", "什么价")):
        return False
    if is_die_fee_question(question) or is_gauge_fee_question(question):
        return False
    if is_procurement_object_question(question):
        return False
    return any(
        word in question
        for word in (
            "待审核",
            "核价进度",
            "审完",
            "作业台",
            "完成情况",
            "还没审",
            "都审了",
            "算完了吗",
            "审核完了",
        )
    )


def is_policy_question(question: str) -> bool:
    return any(term in question for term in _POLICY_TERMS)


def is_base_price_question(question: str) -> bool:
    return bool(any(term in question for term in _BASE_PRICE_TERMS))


def is_winning_thickness_question(question: str) -> bool:
    return any(term in question for term in _WINNING_THICKNESS_TERMS)


def resolve_subject(
    *,
    question: str,
    analyses: list[AnalysisKind],
    filters: dict[str, str],
) -> str:
    """按侧栏菜单语义定 subject（决定取数口径 + 主 Action 落点）。"""
    _ = analyses
    if is_policy_question(question):
        return "steel_price_policy"
    if is_winning_thickness_question(question):
        return "winning_thickness"
    if is_base_price_question(question) and "厚度" not in question:
        return "steel_base_price"
    if any(word in question for word in ("废料销售价", "废料价", "废料月度", "废料月价", "废钢价")):
        return "scrap_price"
    if "废料" in question and "销售" in question:
        return "scrap_price"
    if is_gauge_fee_question(question):
        return "stamping_gauge_fee"
    if is_die_fee_question(question):
        return "stamping_die_fee"
    if is_procurement_object_question(question):
        return "procurement_object"
    if is_ops_workbench_question(question):
        return "ops_workbench"
    if is_welding_fee_question(question):
        return "l0_welding_fee"
    if "焊接单价" in question or (
        "焊接" in question and "单价" in question and "冲压" not in question
    ):
        return "welding_unit_price"
    if is_standard_part_price_question(question):
        return "annual_part_price"
    if any(word in question for word in ("年度零件价", "年度零件价格")):
        return "annual_part_price"
    if "一口价" in question and not any(
        word in question for word in ("成品", "L0", "l0", "总成", "供货总成", "月总账", "采购成本")
    ):
        return "annual_part_price"
    if (
        any(word in question for word in ("外购价", "外购零件价", "外购件价"))
        and "冲压" not in question
    ):
        return "annual_part_price"
    if any(word in question for word in ("包装运输费", "包装运输")):
        return "packaging_transport_fee"
    if "焊接工艺拆解" in question or ("工艺拆解" in question and "焊接" in question):
        return "welding_process_breakdown"
    if any(word in question for word in ("材料清单", "BOM清单", "bom清单", "材料清单列表")):
        return "bom_material"
    if any(word in question for word in ("产品结构", "结构图", "BOM结构")):
        return "bom_material"
    if is_base_price_question(question):
        return "steel_base_price"
    if any(word in question for word in ("联动价", "钢材联动")):
        return "steel_price"
    if any(word in question for word in ("钢材", "钢价")) and "基准" not in question:
        return "steel_price"

    tonnage_filter = filters.get("tonnage")
    if any(word in question for word in ("冲次单价", "冲次价格", "单冲次", "冲次价", "冲次")):
        return "stamping_tonnage"
    if (
        tonnage_filter
        and "冲压" in question
        and any(word in question for word in ("价格", "单价", "多少钱"))
    ):
        return "stamping_tonnage"
    if (
        "冲压" in question
        and "件" not in question
        and any(word in question for word in ("价格", "单价"))
        and tonnage_filter
    ):
        return "stamping_tonnage"

    if "焊接" not in question and (
        "冲压加工费" in question or ("冲压" in question and "加工费" in question)
    ):
        return "stamping_process_fee"
    if not filters.get("part_number") and is_stamping_costing_question(question):
        return "stamping_part"

    part_number = filters.get("part_number")
    if part_number:
        if (
            any(word in question for word in ("存在", "有没有这个", "在不在", "在吗"))
            and "异常" not in question
        ):
            return "part"
        if (
            "有没有" in question
            and "异常" not in question
            and "核价" not in question
            and "成本" not in question
        ):
            return "part"
        if is_drilldown_focused(question, part_number):
            if "焊接" not in question and any(
                word in question for word in ("加工费", "冲压费", "冲压加工费", "工序费")
            ):
                return "stamping_process_fee"
            if any(
                word in question
                for word in (
                    "冲压工艺",
                    "工艺路线",
                    "工艺文件",
                    "工序数",
                    "几道工序",
                    "模具数",
                )
            ):
                return "stamping_process"
            if (
                "工序" in question
                and "加工费" not in question
                and "焊接" not in question
                and any(
                    hint in question for hint in ("冲压", "OP10", "OP20", "模具", "吨位", "工艺")
                )
            ):
                return "stamping_process"
            if is_stamping_costing_question(question):
                return "stamping_part"
            return "l0"
        if "焊接" not in question and any(
            word in question for word in ("加工费", "冲压费", "冲压加工费", "工序费")
        ):
            return "stamping_process_fee"
        if is_standard_part_price_question(question):
            return "annual_part_price"
        if any(
            word in question for word in ("一口价", "年度零件价", "外购价", "外购零件价")
        ) and not any(word in question for word in ("成品", "L0", "l0", "总成", "供货总成")):
            return "annual_part_price"
        if any(word in question for word in ("包装运输费", "包装运输")):
            return "packaging_transport_fee"
        if is_welding_fee_question(question):
            return "l0_welding_fee"
        if "焊接工艺拆解" in question or ("工艺拆解" in question and "焊接" in question):
            return "welding_process_breakdown"
        if any(word in question for word in ("材料清单", "BOM清单", "bom清单")):
            return "bom_material"
        if any(
            word in question
            for word in (
                "冲压工艺",
                "工艺路线",
                "工艺文件",
                "工序数",
                "几道工序",
                "模具数",
            )
        ):
            return "stamping_process"
        if (
            "工序" in question
            and "加工费" not in question
            and "焊接" not in question
            and any(hint in question for hint in ("冲压", "OP10", "OP20", "模具", "吨位", "工艺"))
        ):
            return "stamping_process"
        if is_stamping_costing_question(question):
            return "stamping_part"
        if any(
            word in question
            for word in (
                "成品",
                "成品成本",
                "供货总成",
                "总成成本",
                "总成核价",
                "L0",
                "l0",
            )
        ):
            return "l0"
        return "part"

    if any(
        word in question
        for word in (
            "冲压工艺",
            "工艺路线",
            "工艺文件",
            "工序数",
            "几道工序",
            "模具数",
        )
    ):
        return "stamping_process"
    if (
        "工序" in question
        and "加工费" not in question
        and "焊接" not in question
        and any(hint in question for hint in ("冲压", "OP10", "OP20", "模具", "吨位", "工艺"))
    ):
        return "stamping_process"
    if is_stamping_costing_question(question):
        return "stamping_part"
    if "冲压" in question:
        return "stamping_process"
    if any(
        word in question
        for word in (
            "成品",
            "成品成本",
            "供货总成",
            "总成成本",
            "总成核价",
            "L0",
            "l0",
        )
    ):
        return "l0"
    if "核价" in question and any(word in question for word in ("异常", "有无异常", "有没有异常")):
        return "l0"
    return "cost_total"
