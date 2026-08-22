"""组装 Prompt → 调 LLM；Snapshot 为唯一事实。"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.schemas.llm.analysis_snapshot import AnalysisSnapshot
from app.services.llm.client import LlmChatResult, OpenAiCompatibleClient
from app.services.llm.catalog.field_labels import (
    AGGREGATE_FIELD_LABELS,
    L0_FIELD_LABELS,
)
from app.services.llm.prompts.labels import (
    analyses_key_label_zh,
    audience_label_zh,
    sanitize_report_markdown,
)
from app.services.llm.prompts.registry import PromptRegistry
from app.services.llm.query.comparison_basis import comparability_label_zh


@dataclass(frozen=True, slots=True)
class GeneratedReport:
    markdown_content: str
    prompt_version: str
    prompt_hash: str
    llm_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    audience: str


def _build_field_card() -> str:
  lines = [
      "【字段词典 — 仅供理解 JSON，写入报告时必须全部转为中文白话】",
      "【铁律】",
      "1. 报告正文禁止出现英文字段名、代码术语；见 chinese_style_rules。",
      "2. 数字必须来自 Snapshot；禁止重算、禁止改为万元。",
      "3. 建议可执行，但不发明 Snapshot.actions 以外的系统跳转。",
      "",
      "常见字段中文释义：",
  ]
  label_map = {**L0_FIELD_LABELS, **AGGREGATE_FIELD_LABELS}
  for key in (
      "grand_total",
      "grand_total_sum",
      "total_amount",
      "total_amount_sum",
      "indirect_amount",
      "stamping_amount",
      "purchased_amount",
      "bundle_amount",
      "welding_amount",
      "welding_other_fee",
      "l0_count",
      "ok_count",
      "partial_count",
  ):
      if key in label_map:
          lines.append(f"- {key} → {label_map[key]}")
  lines.extend(
      [
          "- comparability/tight → 同口径可比",
          "- comparability/loose → 口径可能变化",
          "- summary → 概览分析",
          "- buyer_lead → 采购主管",
      ]
  )
  return "\n".join(lines)


_FIELD_CARD = _build_field_card()


class LlmReportGenerator:
    def __init__(
        self,
        *,
        prompt_registry: PromptRegistry | None = None,
        client: OpenAiCompatibleClient | None = None,
    ) -> None:
        self._registry = prompt_registry or PromptRegistry()
        self._client = client or OpenAiCompatibleClient()

    def generate(
        self,
        *,
        snapshot: AnalysisSnapshot,
        audience: str,
    ) -> GeneratedReport:
        prompt = self._registry.resolve(audience)
        system = f"{prompt.system_prompt}\n\n{_FIELD_CARD}"
        context_json = json.dumps(
            snapshot.to_prompt_dict(), ensure_ascii=False, indent=2
        )
        user = prompt.render_user(
            user_question=snapshot.query.user_question,
            report_type=analyses_key_label_zh(snapshot.query.analyses_key()),
            audience=audience_label_zh(prompt.audience),
            context_json=context_json,
        )
        combined_hash = f"{prompt.prompt_hash}:snapshot-v1"
        result: LlmChatResult = self._client.chat(
            system_prompt=system,
            user_prompt=user,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )
        return GeneratedReport(
            markdown_content=sanitize_report_markdown(result.content),
            prompt_version=prompt.prompt_version,
            prompt_hash=combined_hash,
            llm_model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            audience=prompt.audience,
        )

    def render_fallback_markdown(
        self,
        *,
        snapshot: AnalysisSnapshot,
        error_hint: str,
    ) -> str:
        summary = snapshot.summary or {}
        lines = [
            "# 采购分析（规则模板）",
            "",
            f"> 用户问题：{snapshot.query.user_question}",
            "",
            f"> 说明：模型暂不可用（{error_hint}），以下仅拼装系统关键指标。",
            "",
            "## 结论摘要",
            f"- 数据状态：{snapshot.meta.data_message}",
            f"- 可比口径：{comparability_label_zh(snapshot.meta.comparability)}（{snapshot.meta.comparison_basis_label}）",
            f"- 供货总成件数：{summary.get('l0_count', '-')}",
            f"- 总费用合计（元）：{summary.get('grand_total_sum', '-')}",
            f"- 月总账合计（元）：{summary.get('total_amount_sum', '-')}",
            "",
            "## 异常与风险",
        ]
        risk = None
        if snapshot.result.get("kind") == "risk":
            risk = snapshot.result
        elif snapshot.result.get("kind") == "composite":
            risk = (snapshot.result.get("parts") or {}).get("risk")
        if risk and int(risk.get("partial_count") or 0) > 0:
            lines.append(f"- 核算不全件数：{risk.get('partial_count')}")
        else:
            lines.append("- 本次未见核算不全或缺价样本。")
        lines.extend(["", "## 下一步"])
        for action in snapshot.actions[:5]:
            lines.append(f"- {action.label} → `{action.target}`")
        return "\n".join(lines)
