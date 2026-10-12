"""单件问价与下钻焦点（是否只要明细、不要总览）。"""

from __future__ import annotations


def question_asks_part_price(question: str) -> bool:
    """口语问价（含「零件价格」，不必带「是多少」）。"""
    return any(
        phrase in question
        for phrase in (
            "多少钱",
            "什么价",
            "单价多少",
            "价格多少",
            "价格是多少",
            "最新价",
            "核了多少",
            "这个价",
            "零件价格",
            "零件价",
            "的价格",
            "单价",
            "价格",
        )
    )


def is_standard_part_price_question(question: str) -> bool:
    """标准件价格异常走年度零件价，不要落到总成核价或采购成本总览。"""
    if any(
        word in question for word in ("总成核价", "成品核价", "供货总成", "采购对象", "材料清单")
    ):
        return False
    has_part = any(word in question for word in ("标准件", "螺母", "螺栓", "胶块"))
    if not has_part:
        return False
    if "异常" in question:
        return True
    return any(word in question for word in ("价格", "单价", "多少钱", "什么价"))


def is_drilldown_focused(question: str, part_number: str | None) -> bool:
    """单件核价/价格详情：只要明细，不要仪表盘式总览。"""
    if not part_number:
        return False
    if "拼焊费" in question:
        return True
    focus_phrases = (
        "价格详情",
        "核价详情",
        "价格详细",
        "核价详细",
        "价格明细",
        "核价明细",
        "最近一次核价",
        "上次核价",
        "最新核价",
        "最新价",
        "现在什么价",
        "当前核价",
        "核了多少",
        "这个价多少",
        "单价是多少",
    )
    if any(phrase in question for phrase in focus_phrases):
        return True
    overview_words = (
        "总体",
        "总体怎么样",
        "采购成本",
        "总成本",
        "报告",
        "一览",
        "怎么样",
        "概览",
    )
    if question_asks_part_price(question):
        return not any(word in question for word in overview_words)
    return False
