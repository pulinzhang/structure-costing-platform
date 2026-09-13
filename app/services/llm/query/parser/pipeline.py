"""QueryParser 流水线：抽条件 → 对齐 → 规则定 analyses/subject。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.common.part_number import extract_part_number_from_text, sanitize_part_number_token
from app.common.timezone import now
from app.common.tonnage import extract_tonnage_from_text
from app.repositories.llm.cost_analysis_repository import L0CostAnalysisRepository
from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm.client import LlmClientError
from app.services.llm.comparison_basis import default_comparison_basis
from app.services.llm.query.condition_extractor import ConditionExtractor
from app.services.llm.query.entity_aligner import EntityAligner
from app.services.llm.query.intent_router import (
    detect_engine_readiness_question,
    detect_help_topic,
    detect_query_mode,
)
from app.services.llm.query.parser.analyses import resolve_analyses
from app.services.llm.query.parser.draft import parse_time_range_from_draft, rule_fallback_draft
from app.services.llm.query.parser.part_price import question_asks_part_price
from app.services.llm.query.parser.pin_latest import pin_table_latest_month, should_pin_table_latest
from app.services.llm.query.parser.subjects import resolve_subject
from app.services.llm.query.time_range import (
    DefaultScopeMonth,
    draft_has_time_range,
    normalize_time_range,
    question_has_explicit_time,
)
from app.utils.logging_config import get_logger

logger = get_logger("service.llm.query_parser")


class QueryParser:
    def __init__(
        self,
        *,
        extractor: ConditionExtractor | None = None,
        aligner: EntityAligner | None = None,
        cost_repo: L0CostAnalysisRepository | None = None,
    ) -> None:
        self._extractor = extractor or ConditionExtractor()
        self._aligner = aligner or EntityAligner()
        self._cost_repo = cost_repo or L0CostAnalysisRepository()

    def parse(self, db: Session, *, user_question: str) -> AnalysisQuery:
        """LLM 只产出条件草稿；对齐与 analyses/subject 由 Python 决定。"""
        question = (user_question or "").strip()
        if detect_engine_readiness_question(question):
            return self._parse_engine_readiness(db, question=question)
        if detect_query_mode(question) == "usage_help":
            return self._parse_usage_help(question)

        clock = now()
        default = DefaultScopeMonth(year=clock.year, month=clock.month)

        draft: dict[str, Any] = {}
        try:
            draft = self._extractor.extract(
                question,
                current_year=clock.year,
                current_month=clock.month,
            )
        except LlmClientError as exc:
            logger.warning("LLM 条件抽取失败，回退规则: %s", exc)
            draft = rule_fallback_draft(question, default)
            query = self._assemble(
                db,
                question=question,
                draft=draft,
                default=default,
            )
            has_scope_hint = bool(question_has_explicit_time(question) or draft.get("filters"))
            if has_scope_hint:
                return query.model_copy(
                    update={
                        "parser_fallback_level": 4,
                        "parser_data_message": "未能识别具体条件，展示全量数据摘要",
                    }
                )
            return query.model_copy(
                update={
                    "analyses": ["summary", "risk"],
                    "filters": {},
                    "parser_fallback_level": 4,
                    "parser_data_message": "未能识别具体条件，展示全量数据摘要",
                }
            )

        return self._assemble(
            db,
            question=question,
            draft=draft,
            default=default,
        )

    def _parse_engine_readiness(self, db: Session, *, question: str) -> AnalysisQuery:
        clock = now()
        default = DefaultScopeMonth(year=clock.year, month=clock.month)
        draft: dict[str, Any] = {}
        fallback_level = 1
        parser_message: str | None = None
        try:
            draft = self._extractor.extract(
                question,
                current_year=clock.year,
                current_month=clock.month,
            )
        except LlmClientError as exc:
            logger.warning("就绪问句条件抽取失败，规则回退: %s", exc)
            draft = rule_fallback_draft(question, default)
            fallback_level = 4

        time_range = parse_time_range_from_draft(
            draft,
            question=question,
            default=default,
        )
        if not draft_has_time_range(draft) and not question_has_explicit_time(question):
            parser_message = "未识别到时间范围，默认检查当月"

        filter_mentions: list[tuple[str, str]] = []
        filters_raw = draft.get("filters")
        raw_filters: dict[str, Any] = filters_raw if isinstance(filters_raw, dict) else {}
        for key in ("location", "vehicle_model"):
            value = raw_filters.get(key)
            if value is not None and str(value).strip():
                filter_mentions.append((key, str(value).strip()))

        aligned = self._aligner.align(db, mentions=filter_mentions, seed_filters={})
        filters = aligned.filters
        unresolved = list(aligned.unresolved_mentions)

        return AnalysisQuery(
            time_range=time_range,
            filters=filters,
            subject="engine_readiness",
            comparison_basis=default_comparison_basis(same_bom_version=True),
            analyses=["summary"],
            user_question=question,
            unresolved_mentions=unresolved,
            query_mode="engine_readiness",
            parser_fallback_level=fallback_level,
            parser_data_message=parser_message,
        )

    def _parse_usage_help(self, question: str) -> AnalysisQuery:
        clock = now()
        default = DefaultScopeMonth(year=clock.year, month=clock.month)
        time_range = normalize_time_range(user_question=question, default=default)
        help_topic = detect_help_topic(question)
        return AnalysisQuery(
            time_range=time_range,
            filters={},
            subject="usage_help",
            comparison_basis=default_comparison_basis(same_bom_version=True),
            analyses=["summary"],
            user_question=question,
            query_mode="usage_help",
            help_topic=help_topic,
        )

    def _assemble(
        self,
        db: Session,
        *,
        question: str,
        draft: dict[str, Any],
        default: DefaultScopeMonth,
    ) -> AnalysisQuery:
        filter_mentions: list[tuple[str, str]] = []
        filters_raw = draft.get("filters")
        raw_filters: dict[str, Any] = filters_raw if isinstance(filters_raw, dict) else {}
        for key in ("location", "vehicle_model", "bom_version", "part_number", "tonnage"):
            value = raw_filters.get(key)
            if value is None or not str(value).strip():
                continue
            text = str(value).strip()
            if key == "part_number":
                sanitized = sanitize_part_number_token(text)
                if sanitized:
                    filter_mentions.append((key, sanitized))
                continue
            filter_mentions.append((key, text))

        compare_locations_raw = draft.get("compare_locations") or []
        if isinstance(compare_locations_raw, list):
            for location in compare_locations_raw:
                if location and str(location).strip():
                    filter_mentions.append(("location", str(location).strip()))

        part_token = extract_part_number_from_text(question)
        if part_token:
            filter_mentions.append(("part_number", part_token))

        tonnage_token = extract_tonnage_from_text(question)
        if tonnage_token is not None:
            filter_mentions.append(("tonnage", str(tonnage_token)))

        aligned = self._aligner.align(db, mentions=filter_mentions, seed_filters={})
        filters = aligned.filters
        unresolved = list(aligned.unresolved_mentions)
        if tonnage_token is not None:
            filters["tonnage"] = str(tonnage_token)
            unresolved = [item for item in unresolved if not item.startswith("vehicle_model:")]

        compare_aligned: list[str] = []
        if isinstance(compare_locations_raw, list):
            for location in compare_locations_raw:
                text = str(location).strip()
                if not text:
                    continue
                one = self._aligner.align(db, mentions=[("location", text)], seed_filters={})
                resolved = one.filters.get("location")
                if resolved and resolved not in compare_aligned:
                    compare_aligned.append(resolved)
        if len(compare_aligned) >= 2:
            filters["compare_locations"] = ",".join(compare_aligned)
            if "location" not in filters:
                filters["location"] = compare_aligned[0]

        time_range = parse_time_range_from_draft(draft, question=question, default=default)
        parser_fallback_level = 1
        parser_data_message: str | None = None
        if should_pin_table_latest(question, filters.get("part_number")):
            pinned = pin_table_latest_month(
                db,
                cost_repo=self._cost_repo,
                filters=filters,
                time_range=time_range,
            )
            time_range = pinned[0]
            filters = pinned[1]
            parser_data_message = pinned[2]
        elif not draft_has_time_range(draft) and not question_has_explicit_time(question):
            parser_fallback_level = 3
            parser_data_message = "未识别到时间范围，默认分析当月"

        analyses = resolve_analyses(
            question=question,
            part_number=filters.get("part_number"),
            tonnage=filters.get("tonnage"),
            time_span=time_range.month_span(),
            has_compare=bool(filters.get("compare_locations")),
        )
        subject = resolve_subject(
            question=question,
            analyses=analyses,
            filters=filters,
        )
        if subject == "stamping_process":
            analyses = [kind for kind in analyses if kind not in ("trend", "comparison", "risk")]
        if subject == "steel_price_policy":
            if "厚度" in question:
                filters["policy_type"] = "THICKNESS"
            elif "宽度" in question and "加价" in question:
                filters["policy_type"] = "WIDTH"

        return AnalysisQuery(
            time_range=time_range,
            filters=filters,
            subject=subject,
            comparison_basis=default_comparison_basis(same_bom_version=True),
            analyses=analyses,
            user_question=question,
            asks_part_price=question_asks_part_price(question),
            unresolved_mentions=unresolved,
            parser_fallback_level=parser_fallback_level,
            parser_data_message=parser_data_message,
        )
