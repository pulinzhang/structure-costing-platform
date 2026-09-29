"""组装 Prompt → 调 LLM；Snapshot 为唯一事实。"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.schemas.llm.analysis_snapshot import AnalysisSnapshot
from app.services.llm.catalog.field_labels import (
    AGGREGATE_FIELD_LABELS,
    L0_FIELD_LABELS,
)
from app.services.llm.client.openai_compatible import (
    LlmChatResult,
    OpenAiCompatibleClient,
)
from app.services.llm.engine_readiness.runner import render_engine_readiness_markdown
from app.services.llm.prompts.labels import (
    analyses_key_label_zh,
    audience_label_zh,
    sanitize_report_markdown,
)
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
    prompt_preview: str | None = None
    llm_response_preview: str | None = None


def _build_field_card() -> str:
    lines = [
        "【字段词典 — 仅供理解 JSON，写入报告时必须全部转为中文白话】",
        "【铁律】",
        "1. 问什么答什么；禁止套完整报告模板。",
        "2. 报告正文禁止出现英文字段名、代码术语；见 chinese_style_rules。",
        "3. 写合计/全年前必读 JSON 顶层 scope（time_range、month_count）；见 scope_rules。",
        "4. 数字必须来自 Snapshot；禁止重算、禁止改为万元。",
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
        if snapshot.query.query_mode == "usage_help":
            return self._generate_usage_help(snapshot=snapshot)
        if snapshot.query.query_mode == "engine_readiness":
            return self._generate_engine_readiness(snapshot=snapshot)

        prompt = self._registry.resolve(audience)
        system = f"{prompt.system_prompt}\n\n{_FIELD_CARD}"
        context_json = json.dumps(snapshot.to_prompt_dict(), ensure_ascii=False, indent=2)
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
        combined_prompt = f"{system}\n\n{user}"
        markdown = sanitize_report_markdown(result.content)
        return GeneratedReport(
            markdown_content=markdown,
            prompt_version=prompt.prompt_version,
            prompt_hash=combined_hash,
            llm_model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            audience=prompt.audience,
            prompt_preview=combined_prompt[:500],
            llm_response_preview=(result.content or "")[:500],
        )

    def _generate_usage_help(self, *, snapshot: AnalysisSnapshot) -> GeneratedReport:
        prompt = self._registry.resolve_usage_help()
        system = prompt.system_prompt
        context_json = json.dumps(snapshot.to_prompt_dict(), ensure_ascii=False, indent=2)
        user = prompt.render_user(
            user_question=snapshot.query.user_question,
            report_type=analyses_key_label_zh(snapshot.query.analyses_key()),
            audience="使用帮助",
            context_json=context_json,
        )
        combined_hash = f"{prompt.prompt_hash}:usage-help-v1"
        result: LlmChatResult = self._client.chat(
            system_prompt=system,
            user_prompt=user,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )
        combined_prompt = f"{system}\n\n{user}"
        return GeneratedReport(
            markdown_content=sanitize_report_markdown(result.content),
            prompt_version=prompt.prompt_version,
            prompt_hash=combined_hash,
            llm_model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            audience="usage_help",
            prompt_preview=combined_prompt[:500],
            llm_response_preview=(result.content or "")[:500],
        )

    def _generate_engine_readiness(self, *, snapshot: AnalysisSnapshot) -> GeneratedReport:
        prompt = self._registry.resolve_engine_readiness()
        system = prompt.system_prompt
        context_json = json.dumps(snapshot.to_prompt_dict(), ensure_ascii=False, indent=2)
        user = prompt.render_user(
            user_question=snapshot.query.user_question,
            report_type=analyses_key_label_zh(snapshot.query.analyses_key()),
            audience="核算就绪",
            context_json=context_json,
        )
        combined_hash = f"{prompt.prompt_hash}:engine-readiness-v1"
        result: LlmChatResult = self._client.chat(
            system_prompt=system,
            user_prompt=user,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )
        combined_prompt = f"{system}\n\n{user}"
        return GeneratedReport(
            markdown_content=sanitize_report_markdown(result.content),
            prompt_version=prompt.prompt_version,
            prompt_hash=combined_hash,
            llm_model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            audience="engine_readiness",
            prompt_preview=combined_prompt[:500],
            llm_response_preview=(result.content or "")[:500],
        )

    def render_fallback_markdown(
        self,
        *,
        snapshot: AnalysisSnapshot,
        error_hint: str,
    ) -> str:
        if snapshot.query.query_mode == "usage_help":
            return self._render_usage_help_fallback(snapshot=snapshot, error_hint=error_hint)
        if snapshot.query.query_mode == "engine_readiness":
            return self._render_engine_readiness_fallback(
                snapshot=snapshot,
                error_hint=error_hint,
            )

        if isinstance(snapshot.result, dict):
            pinned = snapshot.result.get("table")
            if (
                snapshot.result.get("kind") == "base_price_month_move_over"
                and isinstance(pinned, str)
                and pinned.strip()
            ):
                question = snapshot.query.user_question
                return "\n".join(
                    [
                        f"## {question}",
                        "",
                        f"模型暂不可用（{error_hint}），以下按年、月、基地、牌号列出：",
                        "",
                        pinned,
                    ]
                )

        summary = snapshot.summary or {}
        question = snapshot.query.user_question
        lines = [
            f"## {question}",
            "",
            f"模型暂不可用（{error_hint}），以下为系统数据摘要：",
            "",
        ]
        if snapshot.meta.has_data is False:
            lines.append(snapshot.meta.data_message or "当前查询范围无可用数据。")
        else:
            scope = snapshot.meta.scope
            if scope is not None:
                lines.append(
                    f"- 查询范围：{scope.time_range.get('start')} 至 "
                    f"{scope.time_range.get('end')}（{scope.month_count} 个月有数据）"
                )
            if summary.get("grand_total_sum") is not None:
                lines.append(f"- 总费用合计（元）：{summary.get('grand_total_sum')}")
            if summary.get("total_amount_sum") is not None:
                lines.append(f"- 月总账合计（元）：{summary.get('total_amount_sum')}")
            if summary.get("l0_count") is not None:
                lines.append(f"- 供货总成件数：{summary.get('l0_count')}")
            if summary.get("ok_count") is not None:
                lines.append(f"- 已全部算清：{summary.get('ok_count')}")
        risk: object | None = None
        if snapshot.result.get("kind") == "risk":
            risk = snapshot.result
        elif snapshot.result.get("kind") == "composite":
            parts = snapshot.result.get("parts")
            if isinstance(parts, dict):
                risk = parts.get("risk")
        if isinstance(risk, dict) and int(risk.get("partial_count") or 0) > 0:
            lines.append(f"- 核算不全件数：{risk.get('partial_count')}")
        return "\n".join(lines)

    def _render_engine_readiness_fallback(
        self,
        *,
        snapshot: AnalysisSnapshot,
        error_hint: str,
    ) -> str:
        evidence = snapshot.evidence or {}
        ready_raw = evidence.get("engine_ready")
        if isinstance(ready_raw, dict):
            from app.schemas.vo.costing_engine_vo import CostingEngineReadyVO

            ready = CostingEngineReadyVO.model_validate(ready_raw)
            body = render_engine_readiness_markdown(
                user_question=snapshot.query.user_question,
                ready=ready,
            )
            return f"{body}\n\n> 说明：模型暂不可用（{error_hint}），以上为系统就绪检查结果。"
        return (
            f"## {snapshot.query.user_question}\n\n"
            f"{snapshot.meta.data_message or '就绪检查未完成。'}\n\n"
            f"> 模型暂不可用（{error_hint}）。"
        )

    def _render_usage_help_fallback(
        self,
        *,
        snapshot: AnalysisSnapshot,
        error_hint: str,
    ) -> str:
        chunks_raw = snapshot.result.get("chunks") or []
        chunks = chunks_raw if isinstance(chunks_raw, list) else []
        lines = [
            "# 使用帮助（规则模板）",
            "",
            f"> 用户问题：{snapshot.query.user_question}",
            "",
            f"> 说明：模型暂不可用（{error_hint}），以下为语料摘录。",
            "",
        ]
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            lines.append(f"### {chunk.get('title', '帮助')}")
            lines.append(str(chunk.get("excerpt") or "").strip())
            lines.append("")
        return "\n".join(lines).strip()
