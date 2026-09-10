"""Query Parser：LLM 抽 time/filters → 词典对齐 → Python 定 analyses → AnalysisQuery。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.common.part_number import extract_part_number_from_text, sanitize_part_number_token
from app.common.timezone import now
from app.common.tonnage import extract_tonnage_from_text
from app.schemas.llm.analysis_query import AnalysisKind, AnalysisQuery, TimeRange
from app.services.llm.client import LlmClientError
from app.services.llm.query.comparison_basis import default_comparison_basis
from app.services.llm.query.condition_extractor import ConditionExtractor
from app.services.llm.query.entity_aligner import EntityAligner
from app.services.llm.query.intent_router import (
    detect_engine_readiness_question,
    detect_help_topic,
    detect_query_mode,
)
from app.services.llm.query.time_range import (
    DefaultScopeMonth,
    draft_has_time_range,
    normalize_time_range,
    question_has_explicit_time,
)
from app.utils.logging_config import get_logger

logger = get_logger("service.llm.query_parser")

# 口语「中标价」= 基准价格列表（#/base-price-download），不是「中标厚度价格一览」
_BASE_PRICE_TERMS: tuple[str, ...] = (
    "基准价",
    "基准价格",
    "到厂价",
    "原卷承兑",
    "中标价",
)
_WINNING_THICKNESS_TERMS: tuple[str, ...] = (
    "中标厚度价",
    "中标厚度",
    "中标钢厂厚度",
    "厚度价格一览",
    "厚度价格一览表",
)
# 口语常说「加减价」，少写「政策」；均指加减价政策列表
_POLICY_TERMS: tuple[str, ...] = (
    "加减价",
    "加减价政策",
    "厚度加减",
    "厚度加减价",
    "厚度政策",
    "宽度加价",
    "宽度加减",
    "宽度政策",
    "锌层加减",
    "锌层加价",
)


def _is_stamping_costing_question(question: str) -> bool:
    if any(
        word in question
        for word in ("冲压工艺", "工艺路线", "工艺文件", "冲次单价", "冲次价格", "冲次价", "冲次")
    ):
        return False
    if any(
        word in question
        for word in ("冲压核价", "冲压零件核价", "冲压零件价格", "冲压件成本", "冲压零件价")
    ):
        return True
    return "冲压" in question and any(
        word in question for word in ("核价", "成本", "价格", "零件价")
    )


def _is_welding_fee_question(question: str) -> bool:
    if "焊接单价" in question:
        return False
    if "焊接工艺拆解" in question or ("工艺拆解" in question and "焊接" in question):
        return False
    return any(
        word in question
        for word in ("焊接成本", "焊接费", "焊接核价", "焊接成本计算", "成品焊接费")
    )


def _is_gauge_fee_question(question: str) -> bool:
    return "检具费" in question


def _is_die_fee_question(question: str) -> bool:
    if _is_gauge_fee_question(question):
        return False
    return "模具费" in question


def _is_procurement_object_question(question: str) -> bool:
    if any(word in question for word in ("采购价格协议", "批量零部件价格协议", "导出协议")):
        return False
    if "采购对象" in question:
        return True
    return any(word in question for word in ("还没确认外发", "待确认外发", "外发确认", "确认外发"))


def _is_ops_workbench_question(question: str) -> bool:
    if any(word in question for word in ("异常", "单价为0", "单价是0", "偏差", "多少钱", "什么价")):
        return False
    if _is_die_fee_question(question) or _is_gauge_fee_question(question):
        return False
    if _is_procurement_object_question(question):
        return False
    return any(
        word in question
        for word in (
            "待审核",
            "核价进度",
            "审完",
            "作业台",
            "完成情况",
            "还没审",
            "都审了",
            "算完了吗",
            "审核完了",
        )
    )


def _is_policy_question(question: str) -> bool:
    return any(term in question for term in _POLICY_TERMS)


def _is_base_price_question(question: str) -> bool:
    return bool(any(term in question for term in _BASE_PRICE_TERMS))


def _is_winning_thickness_question(question: str) -> bool:
    return any(term in question for term in _WINNING_THICKNESS_TERMS)


class QueryParser:
    def __init__(
        self,
        *,
        extractor: ConditionExtractor | None = None,
        aligner: EntityAligner | None = None,
    ) -> None:
        self._extractor = extractor or ConditionExtractor()
        self._aligner = aligner or EntityAligner()

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
            draft = self._rule_fallback_draft(question, default)
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
            draft = self._rule_fallback_draft(question, default)
            fallback_level = 4

        time_range = self._parse_time_range(
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

        time_range = self._parse_time_range(draft, question=question, default=default)
        parser_fallback_level = 1
        parser_data_message: str | None = None
        if not draft_has_time_range(draft) and not question_has_explicit_time(question):
            parser_fallback_level = 3
            parser_data_message = "未识别到时间范围，默认分析当月"

        analyses = self._resolve_analyses(
            question=question,
            part_number=filters.get("part_number"),
            tonnage=filters.get("tonnage"),
            time_span=time_range.month_span(),
            has_compare=bool(filters.get("compare_locations")),
        )
        subject = self._resolve_subject(
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
            unresolved_mentions=unresolved,
            parser_fallback_level=parser_fallback_level,
            parser_data_message=parser_data_message,
        )

    def _parse_time_range(
        self,
        draft: dict[str, Any],
        *,
        question: str,
        default: DefaultScopeMonth,
    ) -> TimeRange:
        raw = draft.get("time_range")
        start = None
        end = None
        if isinstance(raw, dict):
            start = str(raw.get("start") or "").strip() or None
            end = str(raw.get("end") or "").strip() or None
        return normalize_time_range(
            user_question=question,
            default=default,
            explicit_start=start,
            explicit_end=end,
        )

    def _resolve_subject(
        self,
        *,
        question: str,
        analyses: list[AnalysisKind],
        filters: dict[str, str],
    ) -> str:
        """按侧栏菜单语义定 subject（决定取数口径 + 主 Action 落点）。"""
        if _is_policy_question(question):
            return "steel_price_policy"
        if _is_winning_thickness_question(question):
            return "winning_thickness"
        if _is_base_price_question(question) and "厚度" not in question:
            return "steel_base_price"
        if any(
            word in question for word in ("废料销售价", "废料价", "废料月度", "废料月价", "废钢价")
        ):
            return "scrap_price"
        if "废料" in question and "销售" in question:
            return "scrap_price"
        if _is_gauge_fee_question(question):
            return "stamping_gauge_fee"
        if _is_die_fee_question(question):
            return "stamping_die_fee"
        if _is_procurement_object_question(question):
            return "procurement_object"
        if _is_ops_workbench_question(question):
            return "ops_workbench"
        if _is_welding_fee_question(question):
            return "l0_welding_fee"
        if "焊接单价" in question or (
            "焊接" in question and "单价" in question and "冲压" not in question
        ):
            return "welding_unit_price"
        if any(word in question for word in ("年度零件价", "年度零件价格")):
            return "annual_part_price"
        if "一口价" in question and not any(
            word in question
            for word in ("成品", "L0", "l0", "总成", "供货总成", "月总账", "采购成本")
        ):
            return "annual_part_price"
        if (
            any(word in question for word in ("外购价", "外购零件价", "外购件价"))
            and "冲压" not in question
        ):
            return "annual_part_price"
        if any(word in question for word in ("包装运输费", "包装运输")):
            return "packaging_transport_fee"
        if "焊接工艺拆解" in question or ("工艺拆解" in question and "焊接" in question):
            return "welding_process_breakdown"
        if any(word in question for word in ("材料清单", "BOM清单", "bom清单", "材料清单列表")):
            return "bom_material"
        if any(word in question for word in ("产品结构", "结构图", "BOM结构")):
            return "bom_material"
        if _is_base_price_question(question):
            return "steel_base_price"
        if any(word in question for word in ("联动价", "钢材联动")):
            return "steel_price"
        if any(word in question for word in ("钢材", "钢价")) and "基准" not in question:
            return "steel_price"

        tonnage_filter = filters.get("tonnage")
        if any(word in question for word in ("冲次单价", "冲次价格", "单冲次", "冲次价", "冲次")):
            return "stamping_tonnage"
        if (
            tonnage_filter
            and "冲压" in question
            and any(word in question for word in ("价格", "单价", "多少钱"))
        ):
            return "stamping_tonnage"
        if (
            "冲压" in question
            and "件" not in question
            and any(word in question for word in ("价格", "单价"))
            and tonnage_filter
        ):
            return "stamping_tonnage"

        if "焊接" not in question and (
            "冲压加工费" in question or ("冲压" in question and "加工费" in question)
        ):
            return "stamping_process_fee"
        if not filters.get("part_number") and _is_stamping_costing_question(question):
            return "stamping_part"

        part_number = filters.get("part_number")
        if part_number:
            if (
                any(word in question for word in ("存在", "有没有这个", "在不在", "在吗"))
                and "异常" not in question
            ):
                return "part"
            if (
                "有没有" in question
                and "异常" not in question
                and "核价" not in question
                and "成本" not in question
            ):
                return "part"
            if self._is_drilldown_focused(question, part_number):
                if "焊接" not in question and any(
                    word in question for word in ("加工费", "冲压费", "冲压加工费", "工序费")
                ):
                    return "stamping_process_fee"
                if any(
                    word in question
                    for word in (
                        "冲压工艺",
                        "工艺路线",
                        "工艺文件",
                        "工序数",
                        "几道工序",
                        "模具数",
                    )
                ):
                    return "stamping_process"
                if (
                    "工序" in question
                    and "加工费" not in question
                    and "焊接" not in question
                    and any(
                        hint in question
                        for hint in ("冲压", "OP10", "OP20", "模具", "吨位", "工艺")
                    )
                ):
                    return "stamping_process"
                if _is_stamping_costing_question(question):
                    return "stamping_part"
                return "l0"
            if "焊接" not in question and any(
                word in question for word in ("加工费", "冲压费", "冲压加工费", "工序费")
            ):
                return "stamping_process_fee"
            if any(
                word in question for word in ("一口价", "年度零件价", "外购价", "外购零件价")
            ) and not any(word in question for word in ("成品", "L0", "l0", "总成", "供货总成")):
                return "annual_part_price"
            if any(word in question for word in ("包装运输费", "包装运输")):
                return "packaging_transport_fee"
            if _is_welding_fee_question(question):
                return "l0_welding_fee"
            if "焊接工艺拆解" in question or ("工艺拆解" in question and "焊接" in question):
                return "welding_process_breakdown"
            if any(word in question for word in ("材料清单", "BOM清单", "bom清单")):
                return "bom_material"
            if any(
                word in question
                for word in (
                    "冲压工艺",
                    "工艺路线",
                    "工艺文件",
                    "工序数",
                    "几道工序",
                    "模具数",
                )
            ):
                return "stamping_process"
            if (
                "工序" in question
                and "加工费" not in question
                and "焊接" not in question
                and any(
                    hint in question for hint in ("冲压", "OP10", "OP20", "模具", "吨位", "工艺")
                )
            ):
                return "stamping_process"
            if _is_stamping_costing_question(question):
                return "stamping_part"
            if any(
                word in question
                for word in (
                    "成品",
                    "成品成本",
                    "供货总成",
                    "总成成本",
                    "总成核价",
                    "L0",
                    "l0",
                )
            ):
                return "l0"
            return "part"

        if any(
            word in question
            for word in (
                "冲压工艺",
                "工艺路线",
                "工艺文件",
                "工序数",
                "几道工序",
                "模具数",
            )
        ):
            return "stamping_process"
        if (
            "工序" in question
            and "加工费" not in question
            and "焊接" not in question
            and any(hint in question for hint in ("冲压", "OP10", "OP20", "模具", "吨位", "工艺"))
        ):
            return "stamping_process"
        if _is_stamping_costing_question(question):
            return "stamping_part"
        if "冲压" in question:
            return "stamping_process"
        if any(
            word in question
            for word in (
                "成品",
                "成品成本",
                "供货总成",
                "总成成本",
                "总成核价",
                "L0",
                "l0",
            )
        ):
            return "l0"
        if "核价" in question and any(
            word in question for word in ("异常", "有无异常", "有没有异常")
        ):
            return "l0"
        # 采购成本 / 总成本等默认 → 成品核价一览
        return "cost_total"

    def _is_drilldown_focused(self, question: str, part_number: str | None) -> bool:
        """单件核价/价格详情：只要明细，不要仪表盘式总览。"""
        if not part_number:
            return False
        focus_phrases = (
            "价格详情",
            "核价详情",
            "价格详细",
            "核价详细",
            "价格明细",
            "核价明细",
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
        if any(phrase in question for phrase in ("多少钱", "什么价", "单价多少", "价格多少")):
            return not any(word in question for word in overview_words)
        return False

    def _resolve_analyses(
        self,
        *,
        question: str,
        part_number: str | None,
        tonnage: str | None,
        time_span: int,
        has_compare: bool,
    ) -> list[AnalysisKind]:
        """analyses 纯规则：不信任 LLM。"""
        if self._is_drilldown_focused(question, part_number):
            result: list[AnalysisKind] = ["drilldown"]
            if time_span > 1 or any(
                word in question for word in ("趋势", "变化", "涨", "跌", "环比", "同比")
            ):
                result.append("trend")
            if has_compare or any(
                word in question for word in ("对比", "比较", "哪个基地", "谁更")
            ):
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
            if any(word in question for word in ("谁贵", "驱动", "贡献", "构成")):
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
        if any(word in question for word in ("谁贵", "驱动", "贡献", "构成", "拆")):
            result.append("drivers")
        if has_compare or any(word in question for word in ("对比", "比较", "哪个基地", "谁更")):
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
            )
        ):
            if "risk" not in result:
                result.append("risk")
            if "drivers" not in result:
                result.append("drivers")
            if time_span > 1 and "trend" not in result:
                result.append("trend")
        if _is_base_price_question(question) and any(
            word in question
            for word in ("异常", "分析", "波动", "怪", "传错", "核对", "上下", "有无")
        ):
            if "trend" not in result:
                result.append("trend")
            if "drivers" not in result:
                result.append("drivers")
        if _is_policy_question(question) and any(
            word in question
            for word in ("异常", "分析", "波动", "怪", "传错", "核对", "上下", "有无")
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
        # 主题报告默认带 drivers（Top 头部件 / 工序最多件）
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
            _is_policy_question(question)
            and any(word in question for word in ("情况", "怎么样", "哪些", "报告", "多少"))
            and "drivers" not in result
        ):
            result.append("drivers")
        if (
            _is_base_price_question(question)
            and any(word in question for word in ("情况", "怎么样", "哪些", "报告", "多少"))
            and "drivers" not in result
        ):
            result.append("drivers")
        if (
            _is_winning_thickness_question(question)
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

    def _rule_fallback_draft(
        self,
        question: str,
        default: DefaultScopeMonth,
    ) -> dict[str, Any]:
        """LLM 不可用：仅抽 time_range + filters。"""
        tr = normalize_time_range(user_question=question, default=default)
        filters: dict[str, str] = {}
        for known in ("青岛", "芜湖", "大连", "鄂尔多斯"):
            if known in question:
                filters["location"] = known
                break
        part_token = extract_part_number_from_text(question)
        if part_token:
            filters["part_number"] = part_token

        return {
            "time_range": {"start": tr.start, "end": tr.end},
            "filters": filters,
            "compare_locations": [],
        }
