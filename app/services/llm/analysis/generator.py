"""组装 System（含 schema_card）+ User → 调 LLM client。"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.llm.client import LlmChatResult, OpenAiCompatibleClient
from app.services.llm.context.aggregator import AggregatedContext
from app.services.llm.prompts.registry import PromptRegistry


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
        aggregated: AggregatedContext,
        user_question: str,
        audience: str,
    ) -> GeneratedReport:
        prompt = self._registry.resolve(audience)
        system = (
            f"{prompt.system_prompt}\n\n"
            f"{aggregated.schema_card_markdown}"
        )
        context_json = (
            __import__("json").dumps(
                aggregated.context, ensure_ascii=False, indent=2
            )
        )
        user = prompt.render_user(
            user_question=user_question,
            report_type=aggregated.report_type,
            audience=prompt.audience,
            context_json=context_json,
        )
        # schema 指纹并入 hash
        from app.services.llm.catalog import (
            build_merged_pack_schema_card,
            schema_card_fingerprint,
        )

        card = build_merged_pack_schema_card(list(aggregated.pack_ids))
        combined_hash = f"{prompt.prompt_hash}:{schema_card_fingerprint(card)}"

        result: LlmChatResult = self._client.chat(
            system_prompt=system,
            user_prompt=user,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )
        return GeneratedReport(
            markdown_content=result.content,
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
        aggregated: AggregatedContext,
        user_question: str,
        error_hint: str,
    ) -> str:
        """LLM 不可用时的规则模板降级（仅 KPI，不编造）。"""
        overview = aggregated.context.get("monthOverview") or {}
        lines = [
            f"# {aggregated.context.get('meta', {}).get('scope', {}).get('location', '')} "
            f"{aggregated.context.get('meta', {}).get('scope', {}).get('year', '')}-"
            f"{aggregated.context.get('meta', {}).get('scope', {}).get('month', '')} "
            f"采购分析（规则模板）",
            "",
            f"> 用户问题：{user_question}",
            "",
            f"> 说明：模型暂不可用（{error_hint}），以下仅拼装系统 KPI，未做自然语言解读。",
            "",
            "## 结论摘要",
            f"- 数据状态：{aggregated.data_message}",
            f"- L0 件数：{overview.get('l0_count', '-')}",
            f"- 总费用合计（元）：{overview.get('grand_total_sum', '-')}",
            f"- 月总账合计（元）：{overview.get('total_amount_sum', '-')}",
            f"- 间接合计（元）：{overview.get('indirect_amount_sum', '-')}",
            "",
            "## 异常与风险",
        ]
        risk = aggregated.context.get("missingPriceRisk") or {}
        partial = risk.get("partial_count")
        if partial:
            lines.append(f"- partial_count={partial}，请至零件列表催缺价。")
        else:
            lines.append("- 本次未见 partial/缺价样本（或未装该 Pack）。")
        lines.extend(["", "## 下周行动清单", "- 确认核价引擎本月已跑通", "- 按缺价清单分工厂催办"])
        return "\n".join(lines)
