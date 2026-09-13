"""成品核价 / 零件存在性 / 单件问价。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.llm.annual_part_price_analysis_repository import (
    AnnualPartPriceAnalysisRepository,
)
from app.repositories.llm.cost_analysis import (
    L0CostAnalysisRepository,
    L0PartPeriodRow,
)
from app.repositories.llm.stamping_cost_analysis_repository import (
    StampingCostAnalysisRepository,
)
from app.repositories.llm.stamping_process_analysis_repository import (
    StampingProcessAnalysisRepository,
)
from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm._money import shift_month
from app.services.llm.analysis.shared.anomaly import build_risks
from app.services.llm.analysis.shared.comparability import resolve_runtime_comparability
from app.services.llm.analysis.shared.comparison import build_location_comparison
from app.services.llm.analysis.shared.compose import compose_result
from app.services.llm.analysis.shared.composition import (
    build_composition_anomalies,
    composition_risk_entry,
)
from app.services.llm.analysis.shared.constants import (
    STANDARD_PART_NAME_KEYS,
    STANDARD_PART_SUPPLY_TYPES,
    STANDARD_PART_UNIT_PRICE_MAX,
)
from app.services.llm.analysis.shared.cost_driver import build_l0_drivers, build_l0_mom_anomalies
from app.services.llm.analysis.shared.cost_trend import build_cost_trend
from app.services.llm.analysis.shared.drilldown import (
    build_annual_leaf_price,
    build_branch_related,
    build_drilldown,
    build_item_price_drilldown,
    build_missing_part_price,
)
from app.services.llm.analysis.shared.formulas import format_missing_price_message
from app.services.llm.analysis.shared.part_lookup import (
    build_part_existence,
    build_part_lookup_summary,
    format_part_lookup_message,
    resolve_part_data_profile,
)
from app.services.llm.analysis.shared.result import AnalysisRunResult
from app.services.llm.analysis.shared.standard_part_price import (
    build_standard_part_price_anomalies,
    standard_part_price_risk_entry,
)
from app.services.llm.analysis.shared.summary import build_summary
from app.services.llm.analysis.stamping.part_cost import build_stamping_cost_drilldown
from app.services.llm.analysis.stamping.process import build_stamping_process_drilldown
from app.services.llm.comparison_basis import resolve_comparability


class AssemblyAnalysis:
    def __init__(self) -> None:
        self._l0_repo = L0CostAnalysisRepository()
        self._annual_part_price_repo = AnnualPartPriceAnalysisRepository()
        self._stamping_repo = StampingCostAnalysisRepository()
        self._stamping_process_repo = StampingProcessAnalysisRepository()

    def run_part(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        if self.should_run_part_price_drilldown(query):
            return self.run_part_price_drilldown(db, query)
        return self.run_part_lookup(db, query)

    def run_default(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        if self.is_part_price_drilldown(query):
            return self.run_part_price_drilldown(db, query)
        return self.run_l0(db, query)

    def is_part_price_drilldown(self, query: AnalysisQuery) -> bool:
        return (
            "drilldown" in query.analyses
            and bool(query.part_number())
            and "summary" not in query.analyses
        )

    def should_run_part_price_drilldown(self, query: AnalysisQuery) -> bool:
        if self.is_part_price_drilldown(query):
            return True
        return bool(query.part_number()) and query.asks_part_price

    def run_part_price_drilldown(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """单件问价：先核价卡，再核价表材料行，再年度零件价。"""
        tr = query.time_range
        token = query.part_number() or ""
        part_rows = self._query_assembly_part_rows(
            db,
            query,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
        )
        drilldown = build_drilldown(part_rows, part_number=token)
        if drilldown.get("found"):
            if drilldown.get("fork") == "sub_assembly":
                drilldown["related"] = self._related_branch_costing(db, query, drilldown)
            return self._part_price_result(
                query,
                drilldown,
                has_data=True,
                detail="来源=核价表",
            )

        item_rows = self._l0_repo.query_item_price_rows(
            db,
            part_number=token,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
        )
        if not item_rows and (query.location() or query.vehicle_model() or query.bom_version()):
            item_rows = self._l0_repo.query_item_price_rows(
                db,
                part_number=token,
                start_year=tr.start_year,
                start_month=tr.start_month,
                end_year=tr.end_year,
                end_month=tr.end_month,
            )
        if item_rows:
            payload = build_item_price_drilldown(item_rows, part_token=token)
            if payload.get("found"):
                return self._part_price_result(
                    query,
                    payload,
                    has_data=True,
                    detail="来源=核价表材料明细",
                )

        annual_rows = self._annual_part_price_repo.query_rows(
            db,
            location=query.location(),
            start_year=tr.end_year,
            end_year=tr.end_year,
            part_number=token,
        )
        if not annual_rows:
            annual_rows = self._annual_part_price_repo.query_rows(
                db,
                location=None,
                start_year=None,
                end_year=None,
                part_number=token,
            )
        head = self._annual_part_price_repo.pick_best_row(annual_rows, part_token=token)
        if head is not None:
            payload = build_annual_leaf_price(head, part_token=token)
            return self._part_price_result(
                query,
                payload,
                has_data=True,
                detail="来源=年度零件价列表",
            )
        return self._part_price_result(
            query,
            build_missing_part_price(token),
            has_data=False,
            detail="核价表与年度零件价列表均未命中",
        )

    def _part_price_result(
        self,
        query: AnalysisQuery,
        drilldown: dict[str, Any],
        *,
        has_data: bool,
        detail: str,
    ) -> AnalysisRunResult:
        base_message = query.parser_data_message or ""
        parts = [part for part in (base_message, detail) if part]
        return AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=has_data,
            data_message="；".join(parts),
            result=drilldown,
        )

    def _query_assembly_part_rows(
        self,
        db: Session,
        query: AnalysisQuery,
        *,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        trace_id: str | None = None,
    ) -> list[L0PartPeriodRow]:
        part_token = query.part_number()
        return self._l0_repo.query_part_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
            start_year=start_year,
            start_month=start_month,
            end_year=end_year,
            end_month=end_month,
            part_number=part_token or None,
            tree_root_only=not bool(part_token),
            trace_id=trace_id,
        )

    def _related_branch_costing(
        self,
        db: Session,
        query: AnalysisQuery,
        drilldown: dict[str, Any],
    ) -> dict[str, Any]:
        latest = drilldown.get("latest") or {}
        year = int(latest.get("year") or query.time_range.end_year)
        month = int(latest.get("month_number") or query.time_range.end_month)
        part_number = str(drilldown.get("part_number") or query.part_number() or "")
        items = (
            self._l0_repo.query_card_item_rows(
                db,
                year=year,
                month=month,
                part_number=part_number,
                location=query.location() or latest.get("location"),
                vehicle_model=query.vehicle_model() or latest.get("vehicle_model"),
                bom_version=query.bom_version() or latest.get("bom_version"),
            )
            if part_number
            else []
        )
        parent = None
        root_part_number = drilldown.get("root_part_number")
        if root_part_number:
            parent_rows = self._l0_repo.query_part_rows(
                db,
                location=query.location() or latest.get("location"),
                vehicle_model=query.vehicle_model() or latest.get("vehicle_model"),
                bom_version=query.bom_version() or latest.get("bom_version"),
                start_year=year,
                start_month=month,
                end_year=year,
                end_month=month,
                part_number=str(root_part_number),
                tree_root_only=True,
            )
            if parent_rows:
                parent = sorted(parent_rows, key=lambda row: (row.year, row.month))[-1]
        return build_branch_related(parent=parent, items=items)

    def run_part_lookup(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """指定零件号：同时在 L0、冲压价、冲压工艺中检索。"""
        tr = query.time_range
        part_token = query.part_number() or ""
        l0_rows = self._query_assembly_part_rows(
            db,
            query,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
        )
        stamping_rows = self._stamping_repo.query_part_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            part_number=part_token or None,
        )
        process_rows = self._stamping_process_repo.query_part_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            version=query.bom_version(),
            part_number=part_token or None,
        )

        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(l0_rows or stamping_rows or process_rows),
            data_message=format_part_lookup_message(
                l0_rows=l0_rows,
                stamping_rows=stamping_rows,
                process_rows=process_rows,
            ),
        )

        if "summary" in query.analyses:
            out.summary = build_part_lookup_summary(
                query_token=part_token,
                l0_rows=l0_rows,
                stamping_rows=stamping_rows,
                process_rows=process_rows,
            )

        profile = resolve_part_data_profile(
            l0_rows=l0_rows,
            stamping_rows=stamping_rows,
            process_rows=process_rows,
        )
        drilldown_only = "drilldown" in query.analyses and "summary" not in query.analyses
        skip_cross_existence = drilldown_only and profile.primary_source == "l0" and bool(l0_rows)

        parts_result: dict[str, Any] = {}
        if not skip_cross_existence and (
            "drilldown" in query.analyses or "summary" in query.analyses
        ):
            parts_result["existence"] = build_part_existence(
                query_token=part_token,
                l0_rows=l0_rows,
                stamping_rows=stamping_rows,
                process_rows=process_rows,
            )
        if "drilldown" in query.analyses:
            if l0_rows:
                l0_drilldown = build_drilldown(l0_rows, part_number=part_token)
                if l0_drilldown.get("fork") == "sub_assembly":
                    l0_drilldown["related"] = self._related_branch_costing(db, query, l0_drilldown)
                parts_result["l0_drilldown"] = l0_drilldown
            if profile.stamping_cost_applicable:
                parts_result["stamping_cost_drilldown"] = build_stamping_cost_drilldown(
                    stamping_rows, part_number=part_token
                )
            if profile.stamping_process_applicable:
                part, processes = self._stamping_process_repo.query_process_details(
                    db,
                    part_number=part_token,
                    location=query.location(),
                    vehicle_model=query.vehicle_model(),
                    version=query.bom_version(),
                )
                parts_result["stamping_process_drilldown"] = build_stamping_process_drilldown(
                    part,
                    processes,
                    part_number=part_token,
                )

        out.result = compose_result(parts_result, default_kind="part_existence")
        out.evidence["part_lookup"] = {
            "l0_rows": len(l0_rows),
            "stamping_cost_rows": len(stamping_rows),
            "stamping_process_rows": len(process_rows),
        }
        return out

    def run_l0(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        tr = query.time_range
        location = query.location()
        vehicle_model = query.vehicle_model()
        bom_version = query.bom_version()
        compare_raw = query.filter_get("compare_locations")
        locations = (
            [item.strip() for item in compare_raw.split(",") if item.strip()]
            if compare_raw
            else None
        )
        trace_id = query.trace_id

        monthly = self._l0_repo.query_monthly_totals(
            db,
            location=None if locations else location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            locations=locations,
            trace_id=trace_id,
        )

        need_parts = any(
            kind in query.analyses for kind in ("drivers", "risk", "drilldown", "trend", "summary")
        )
        peek_previous_month = query.time_range.month_span() == 1 and any(
            kind in query.analyses for kind in ("risk", "drivers", "trend")
        )
        part_rows: list[L0PartPeriodRow] = []
        filtered_missing = 0
        if need_parts:
            part_start_year, part_start_month = tr.start_year, tr.start_month
            if peek_previous_month:
                part_start_year, part_start_month = shift_month(tr.start_year, tr.start_month, -1)
            part_rows = self._query_assembly_part_rows(
                db,
                query,
                start_year=part_start_year,
                start_month=part_start_month,
                end_year=tr.end_year,
                end_month=tr.end_month,
                trace_id=trace_id,
            )
            filtered_missing = self._l0_repo.count_filtered_missing_price(
                db,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                start_year=tr.start_year,
                start_month=tr.start_month,
                end_year=tr.end_year,
                end_month=tr.end_month,
                trace_id=trace_id,
            )

        focus_part_rows = (
            [row for row in part_rows if row.year == tr.end_year and row.month == tr.end_month]
            if peek_previous_month
            else part_rows
        )

        comparability, comparability_note = resolve_runtime_comparability(
            basis=query.comparison_basis,
            part_rows=focus_part_rows,
        )
        out = AnalysisRunResult(
            comparability=comparability,
            comparability_note=comparability_note,
            filtered_missing_price_count=filtered_missing,
        )
        parts_result: dict[str, Any] = {}
        driver_top_n = query.top_n()

        if "summary" in query.analyses:
            out.summary = build_summary(monthly, part_rows=focus_part_rows or None)

        if "trend" in query.analyses:
            single_month = query.time_range.start == query.time_range.end
            trend_result = build_cost_trend(
                monthly,
                basis=query.comparison_basis,
                single_month=single_month,
            )
            parts_result["trend"] = trend_result
            out.anomaly_note = trend_result.get("anomaly_note")

        if "drivers" in query.analyses:
            parts_result["drivers"] = build_l0_drivers(part_rows, top_n=driver_top_n)

        if "comparison" in query.analyses:
            parts_result["comparison"] = build_location_comparison(
                monthly, basis=query.comparison_basis
            )

        if "risk" in query.analyses:
            risk_payload = build_risks(
                focus_part_rows,
                filtered_missing_price_count=filtered_missing,
            )
            composition = build_composition_anomalies(
                self._l0_repo.query_composition_lines(
                    db,
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    start_year=tr.start_year,
                    start_month=tr.start_month,
                    end_year=tr.end_year,
                    end_month=tr.end_month,
                    part_number=query.part_number(),
                    trace_id=trace_id,
                )
            )
            parts_result["composition_anomalies"] = composition
            composition_risk = composition_risk_entry(composition)
            if composition_risk is not None:
                risk_payload["risks"].append(composition_risk)
                risk_payload["composition_dominance_count"] = composition_risk["count"]
            standard = build_standard_part_price_anomalies(
                self._l0_repo.query_standard_part_price_lines(
                    db,
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    start_year=tr.start_year,
                    start_month=tr.start_month,
                    end_year=tr.end_year,
                    end_month=tr.end_month,
                    part_number=query.part_number(),
                    min_unit_price=Decimal(STANDARD_PART_UNIT_PRICE_MAX),
                    supply_types=STANDARD_PART_SUPPLY_TYPES,
                    name_keys=STANDARD_PART_NAME_KEYS,
                    trace_id=trace_id,
                )
            )
            parts_result["standard_part_anomalies"] = standard
            standard_risk = standard_part_price_risk_entry(standard)
            if standard_risk is not None:
                risk_payload["risks"].append(standard_risk)
                risk_payload["standard_part_high_price_count"] = standard_risk["count"]
            parts_result["risk"] = risk_payload

        if part_rows and any(kind in query.analyses for kind in ("risk", "drivers", "trend")):
            focus_month = None
            if peek_previous_month:
                focus_month = f"{tr.end_year:04d}-{tr.end_month:02d}"
            parts_result["mom_anomalies"] = build_l0_mom_anomalies(
                part_rows,
                focus_month=focus_month,
            )

        if "drilldown" in query.analyses:
            part_number = query.part_number() or ""
            drilldown = build_drilldown(part_rows, part_number=part_number)
            if drilldown.get("fork") == "sub_assembly":
                drilldown["related"] = self._related_branch_costing(db, query, drilldown)
            parts_result["drilldown"] = drilldown

        out.result = compose_result(parts_result, default_kind="summary")
        out.has_data = bool(monthly) or bool(part_rows)
        base_message = query.parser_data_message or ""
        missing_message = format_missing_price_message(filtered_missing)
        if monthly:
            part_total = (
                out.summary.get("l0_count") if out.summary else max(row.l0_count for row in monthly)
            )
            detail = f"L0 月切片={len(monthly)}，" f"供货总成={part_total}件（按零件号去重）"
            parts = [part for part in (base_message, missing_message, detail) if part]
            out.data_message = "；".join(parts)
        elif part_rows:
            detail = f"L0 零件行={len(part_rows)}"
            parts = [part for part in (base_message, missing_message, detail) if part]
            out.data_message = "；".join(parts)
        else:
            out.data_message = base_message or missing_message or "当前查询范围无核价结果"

        if out.summary is None and monthly:
            out.summary = build_summary(monthly, part_rows=focus_part_rows or None)

        out.evidence["monthly_totals"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "location": row.location,
                "grand_total_sum": str(row.grand_total_sum),
                "l0_count": row.l0_count,
            }
            for row in monthly[:36]
        ]
        return out
