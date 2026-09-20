"""analyses[] 纯规则：不信任 LLM。"""

from __future__ import annotations

from app.schemas.llm.analysis_query import AnalysisKind
from app.services.llm.query.parser.part_price import is_drilldown_focused
from app.services.llm.query.parser.subjects import (
    asks_engineering_change_price_compare,
    is_base_price_question,
    is_policy_question,
    is_winning_thickness_question,
)
from app.services.llm.query.time_range import asks_latest_costing

COMPARE_QUESTION_WORDS: tuple[str, ...] = ("对比", "比较", "哪个基地", "谁更", "变更前后")


def question_has_compare_signal(question: str) -> bool:
    return any(word in (question or "") for word in COMPARE_QUESTION_WORDS) or (
        asks_engineering_change_price_compare(question or "")
    )


def resolve_analyses(
    *,
    question: str,
    part_number: str | None,
    tonnage: str | None,
    time_span: int,
    has_compare: bool,
) -> list[AnalysisKind]:
    if is_drilldown_focused(question, part_number):
        result: list[AnalysisKind] = ["drilldown"]
        wants_trend = any(word in question for word in ("趋势", "变化", "涨", "跌", "环比", "同比"))
        if wants_trend or (time_span > 1 and not asks_latest_costing(question)):
            result.append("trend")
        if has_compare or question_has_compare_signal(question):
            result.append("comparison")
        if any(word in question for word in ("缺价", "partial", "算不全", "跑不起来")):
            result.append("risk")
        if any(
            word in question
            for word in (
                "异常",
                "风险",
                "单价为0",
                "单价是0",
                "偏差",
                "上月",
            )
        ):
            if "risk" not in result:
                result.append("risk")
            if "drivers" not in result:
                result.append("drivers")
        if any(word in question for word in ("概览", "总体", "汇总")):
            result.insert(0, "summary")
        if any(word in question for word in ("谁贵", "贵在哪", "驱动", "贡献", "构成")):
            result.append("drivers")
        seen_focus: list[AnalysisKind] = []
        for kind in result:
            if kind not in seen_focus:
                seen_focus.append(kind)
        return seen_focus or ["drilldown"]

    result = ["summary"]
    if time_span > 1 or any(
        word in question for word in ("趋势", "变化", "涨", "跌", "环比", "同比")
    ):
        result.append("trend")
    if any(word in question for word in ("谁贵", "贵在哪", "驱动", "贡献", "构成", "拆")):
        result.append("drivers")
    if has_compare or question_has_compare_signal(question):
        result.append("comparison")
    if any(word in question for word in ("缺价", "partial", "算不全", "跑不起来")):
        result.append("risk")
    if any(
        word in question
        for word in (
            "风险",
            "异常",
            "最大",
            "突出",
            "核对",
            "有问题",
            "什么问题",
            "哪个零件",
            "哪个月",
            "波动",
            "怪",
            "传错",
            "上传错",
            "有无异常",
            "单价为0",
            "单价是0",
            "偏差",
            "上月",
            "待审核",
            "进度",
            "审完",
            "还没确认",
            "未完成",
            "算不全",
            "缺供应商",
            "未指定供应商",
            "待确认外发",
            "没有供应商",
            "没指定供应商",
            "没供应商",
            "无供应商",
            "停用件",
            "此件不装",
            "完成停止",
        )
    ):
        if "risk" not in result:
            result.append("risk")
        if "drivers" not in result:
            result.append("drivers")
        if time_span > 1 and "trend" not in result:
            result.append("trend")
    if is_base_price_question(question) and any(
        word in question for word in ("异常", "分析", "波动", "怪", "传错", "核对", "上下", "有无")
    ):
        if "trend" not in result:
            result.append("trend")
        if "drivers" not in result:
            result.append("drivers")
    if is_policy_question(question) and any(
        word in question for word in ("异常", "分析", "波动", "怪", "传错", "核对", "上下", "有无")
    ):
        if "trend" not in result:
            result.append("trend")
        if "drivers" not in result:
            result.append("drivers")
    if part_number or "零件号" in question:
        result.append("drilldown")
    if (
        tonnage or any(word in question for word in ("冲次", "吨位"))
    ) and "drilldown" not in result:
        result.append("drilldown")
    if (
        any(word in question for word in ("冲压", "冲压工艺", "工艺路线", "工序", "工艺文件"))
        and "drivers" not in result
    ):
        result.append("drivers")
    if (
        any(word in question for word in ("成品", "采购", "总成"))
        and any(word in question for word in ("报告", "一览", "成本"))
        and "drivers" not in result
    ):
        result.append("drivers")
    if (
        is_policy_question(question)
        and any(word in question for word in ("情况", "怎么样", "哪些", "报告", "多少"))
        and "drivers" not in result
    ):
        result.append("drivers")
    if (
        is_base_price_question(question)
        and any(word in question for word in ("情况", "怎么样", "哪些", "报告", "多少"))
        and "drivers" not in result
    ):
        result.append("drivers")
    if (
        is_winning_thickness_question(question)
        and any(word in question for word in ("情况", "怎么样", "哪些", "报告", "多少"))
        and "drivers" not in result
    ):
        result.append("drivers")
    if (
        any(word in question for word in ("废料", "废钢"))
        and any(word in question for word in ("情况", "怎么样", "哪些", "报告", "多少", "销售"))
        and "drivers" not in result
    ):
        result.append("drivers")
    seen: list[AnalysisKind] = []
    for kind in result:
        if kind not in seen:
            seen.append(kind)
    return seen or ["summary"]
