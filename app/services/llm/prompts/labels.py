"""报告类型 / 受众等 Prompt 展示用中文标签。"""

from __future__ import annotations

import re

ANALYSIS_KIND_LABEL_ZH: dict[str, str] = {
    "summary": "概览分析",
    "trend": "趋势分析",
    "drivers": "动因分析",
    "comparison": "对比分析",
    "risk": "风险分析",
    "drilldown": "核价详情",
}

AUDIENCE_LABEL_ZH: dict[str, str] = {
    "buyer": "采购员",
    "buyer_lead": "采购主管",
    "costing": "核价工程师",
    "sales_quote": "销售报价",
    "exec": "管理层",
}


def analyses_key_label_zh(analyses_key: str) -> str:
    if analyses_key == "usage_help":
        return "使用帮助"
    if analyses_key == "engine_readiness":
        return "核算就绪检查"
    parts = [part.strip() for part in analyses_key.split(",") if part.strip()]
    if not parts:
        return ANALYSIS_KIND_LABEL_ZH["summary"]
    labels = [ANALYSIS_KIND_LABEL_ZH.get(part, part) for part in parts]
    return "、".join(labels)


def audience_label_zh(audience: str) -> str:
    text = audience.strip()
    return AUDIENCE_LABEL_ZH.get(text, text)


_BOILERPLATE_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:报告类型|受众|目标受众|数据生成日期|生成日期)\s*[：:|｜]",
    re.IGNORECASE,
)


def sanitize_report_markdown(content: str) -> str:
    """兜底：修正残留英文标签，并剔除不应展示的报告元信息行。"""
    result = content
    replacements = {**ANALYSIS_KIND_LABEL_ZH, **AUDIENCE_LABEL_ZH}
    for english, chinese in replacements.items():
        result = re.sub(
            rf"(报告类型\s*[：:]\s*){re.escape(english)}\b",
            rf"\1{chinese}",
            result,
            flags=re.IGNORECASE,
        )
        result = re.sub(
            rf"(受众\s*[：:]\s*){re.escape(english)}\b",
            rf"\1{chinese}",
            result,
            flags=re.IGNORECASE,
        )
        result = re.sub(
            rf"(报告类型\s+){re.escape(english)}\b",
            rf"\1{chinese}",
            result,
            flags=re.IGNORECASE,
        )
    result = re.sub(r"\bdashboard\b", "分析", result, flags=re.IGNORECASE)
    result = re.sub(r"仪表盘", "分析", result)
    filtered_lines = [
        line for line in result.splitlines() if not _BOILERPLATE_LINE_RE.match(line.strip())
    ]
    return "\n".join(filtered_lines).strip()
