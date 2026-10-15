"""Prompt 中文标签单元测试。"""

from __future__ import annotations

from app.services.llm.prompts.labels import (
    analyses_key_label_zh,
    audience_label_zh,
    sanitize_report_markdown,
)


def test_analyses_key_label_zh() -> None:
    assert analyses_key_label_zh("summary") == "概览分析"
    assert analyses_key_label_zh("summary,trend") == "概览分析、趋势分析"
    assert analyses_key_label_zh("usage_help") == "操作说明"
    assert analyses_key_label_zh("engine_readiness") == "核价条件检查"
    assert analyses_key_label_zh("not_a_kind") == "分析"


def test_audience_label_zh() -> None:
    assert audience_label_zh("buyer_lead") == "采购主管"


def test_sanitize_report_markdown_report_type() -> None:
    raw = "报告类型：summary ｜ 受众：buyer_lead"
    assert sanitize_report_markdown(raw) == ""


def test_sanitize_report_markdown_renames_current_mill() -> None:
    raw = "| 这次钢厂 | 这次基准价（元/吨） |"
    assert sanitize_report_markdown(raw) == "| 本月钢厂 | 本月基准价（元/吨） |"
