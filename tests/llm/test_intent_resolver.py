# -*- coding: utf-8 -*-
"""意图解析与幂等指纹单测。"""

from __future__ import annotations

from app.services.llm.analysis.idempotency import (
    build_idempotency_key,
    question_fingerprint,
)
from app.services.llm.analysis.intent_resolver import resolve_intent


def test_auto_defaults_to_dashboard() -> None:
    result = resolve_intent(
        report_type="auto",
        user_question="2025年01月的情况怎么样",
    )
    assert result.resolved_report_type == "dashboard"
    assert result.intent_source == "default_dashboard"


def test_auto_steel_keyword() -> None:
    result = resolve_intent(
        report_type="auto",
        user_question="本月钢材吨价哪些在涨？",
    )
    assert result.resolved_report_type == "steel"
    assert result.intent_source == "rule"


def test_auto_gate_keyword() -> None:
    result = resolve_intent(
        report_type="auto",
        user_question="为什么这个月核价跑不起来？主数据缺什么",
    )
    assert result.resolved_report_type == "gate"


def test_chip_dashboard_explicit() -> None:
    result = resolve_intent(
        report_type="dashboard",
        user_question="总体怎么样",
        audience="buyer_lead",
        prompt_id="Q01",
    )
    assert result.resolved_report_type == "dashboard"
    assert result.intent_source == "chip"
    assert result.audience == "buyer_lead"


def test_part_drilldown_without_part_falls_back() -> None:
    result = resolve_intent(
        report_type="part_drilldown",
        user_question="帮我解读一下",
        prompt_id="Q51",
    )
    assert result.resolved_report_type == "dashboard"


def test_idempotency_changes_with_question() -> None:
    key_a = build_idempotency_key(
        report_type="auto",
        audience="buyer_lead",
        location="青岛",
        year=2025,
        month=1,
        vehicle_model="T28",
        bom_version="D/00",
        user_question="总体怎么样",
        user_id=1,
    )
    key_b = build_idempotency_key(
        report_type="auto",
        audience="buyer_lead",
        location="青岛",
        year=2025,
        month=1,
        vehicle_model="T28",
        bom_version="D/00",
        user_question="钢材怎么样",
        user_id=1,
    )
    assert key_a != key_b
    assert question_fingerprint("总体怎么样") == question_fingerprint("  总体怎么样  ")
