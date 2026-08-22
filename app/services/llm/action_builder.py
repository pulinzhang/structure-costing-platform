"""规则生成 Actions（含 NAVIGATE 深链带参）。"""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlencode

from app.schemas.llm.analysis_query import AnalysisQuery
from app.schemas.llm.analysis_snapshot import AnalysisAction
from app.services.llm.analysis.part_lookup import resolve_part_lookup_menu_keys
from app.services.llm.analysis.runner import AnalysisRunResult
from app.services.llm.menu_catalog import (
    SUBJECT_MENU,
    build_list_params,
    build_list_params_for_page,
    resolve_menu_target,
)
from app.services.llm.usage.actions import build_usage_help_actions
from app.services.llm.usage.corpus import CorpusChunk


class ActionBuilder:
    def build(
        self,
        *,
        query: AnalysisQuery,
        run: AnalysisRunResult,
    ) -> list[AnalysisAction]:
        if query.query_mode == "usage_help":
            return self._build_usage_help(query=query, run=run)

        actions: list[AnalysisAction] = []
        part_number = query.part_number()

        if query.subject == "part" and part_number:
            question = query.user_question or ""
            cross_check = any(
                word in question
                for word in ("存在", "有没有", "在不在", "有没有这个", "在吗")
            )
            lookup = run.evidence.get("part_lookup") or {}
            menu_keys = resolve_part_lookup_menu_keys(
                cross_check=cross_check,
                l0_row_count=int(lookup.get("l0_rows") or 0),
                stamping_cost_row_count=int(lookup.get("stamping_cost_rows") or 0),
                stamping_process_row_count=int(lookup.get("stamping_process_rows") or 0),
            )
            for menu_key in menu_keys:
                target = SUBJECT_MENU[menu_key]
                params = cast(
                    dict[str, str | list[str]],
                    build_list_params_for_page(query, target.hash_page),
                )
                actions.append(
                    AnalysisAction(
                        action_id=target.action_id,
                        type="NAVIGATE",
                        label=target.label,
                        target=self._deep_link(f"#/{target.hash_page}", params),
                        permission="op:llm-analysis:view",
                        params=params,
                    )
                )
            return actions

        params = cast(
            dict[str, str | list[str]],
            build_list_params(query),
        )
        target = resolve_menu_target(query)

        actions.append(
            AnalysisAction(
                action_id=target.action_id,
                type="NAVIGATE",
                label=target.label,
                target=self._deep_link(f"#/{target.hash_page}", params),
                permission="op:llm-analysis:view",
                params=params,
            )
        )

        if part_number:
            skip_drilldown = query.subject in (
                "l0",
                "stamping_part",
                "stamping_process",
                "stamping_process_fee",
                "annual_part_price",
                "packaging_transport_fee",
                "bom_material",
                "welding_process_breakdown",
                "l0_welding_fee",
            )
            if skip_drilldown:
                return actions
            if query.subject == "stamping_process":
                drill_label = f"查看 {part_number} 工艺明细"
            elif query.subject == "stamping_process_fee":
                drill_label = f"查看 {part_number} 加工费明细"
            elif query.subject == "annual_part_price":
                drill_label = f"查看 {part_number} 年度零件价明细"
            elif query.subject == "packaging_transport_fee":
                drill_label = f"查看 {part_number} 包装运输费明细"
            elif query.subject == "bom_material":
                drill_label = f"查看 {part_number} 材料清单明细"
            elif query.subject == "welding_process_breakdown":
                drill_label = f"查看 {part_number} 焊接工艺拆解明细"
            elif query.subject == "l0_welding_fee":
                drill_label = f"查看 {part_number} 成品焊接费明细"
            elif (
                query.subject == "stamping_part"
                or "冲压" in (query.user_question or "")
            ):
                drill_label = f"查看 {part_number} 冲压件明细"
            else:
                drill_label = f"查看 {part_number} 核价明细"
            actions.append(
                AnalysisAction(
                    action_id=f"drilldown_part_{part_number}",
                    type="NAVIGATE",
                    label=drill_label,
                    target=self._deep_link(f"#/{target.hash_page}", params),
                    permission="op:llm-analysis:view",
                    params=params,
                )
            )

        risk = _extract_risk(run)
        if risk and int(risk.get("partial_count") or 0) > 0:
            risk_label = (
                "打开一览并核对失败件"
                if query.subject == "stamping_part"
                else "查看缺价 / partial 清单"
            )
            actions.append(
                AnalysisAction(
                    action_id="open_risk_hint",
                    type="NAVIGATE",
                    label=risk_label,
                    target=self._deep_link(f"#/{target.hash_page}", params),
                    permission="op:llm-analysis:view",
                    params=params,
                )
            )

        return actions

    def _build_usage_help(
        self,
        *,
        query: AnalysisQuery,
        run: AnalysisRunResult,
    ) -> list[AnalysisAction]:
        raw_chunks = run.evidence.get("corpus_chunks") or []
        chunks: list[CorpusChunk] = []
        for item in raw_chunks:
            if not isinstance(item, dict):
                continue
            chunks.append(
                CorpusChunk(
                    chunk_id=str(item.get("chunk_id") or ""),
                    title=str(item.get("title") or ""),
                    text=str(item.get("text") or ""),
                    source_page=str(item.get("source_page") or "help.html"),
                    anchor=str(item.get("anchor") or "start"),
                    keywords=tuple(str(k) for k in (item.get("keywords") or [])),
                    menu_hash=(
                        str(item["menu_hash"])
                        if item.get("menu_hash") is not None
                        else None
                    ),
                )
            )
        return build_usage_help_actions(query, chunks)

    def _deep_link(self, path: str, params: dict[str, str | list[str]]) -> str:
        cleaned = {key: value for key, value in params.items() if value}
        query = urlencode(cleaned)
        base = path if path.startswith("#") else f"#{path}"
        return f"{base}?{query}" if query else base


def _extract_risk(run: AnalysisRunResult) -> dict[str, Any] | None:
    if run.result.get("kind") == "risk":
        return run.result
    if run.result.get("kind") == "composite":
        risk = (run.result.get("parts") or {}).get("risk")
        return risk if isinstance(risk, dict) else None
    return None
