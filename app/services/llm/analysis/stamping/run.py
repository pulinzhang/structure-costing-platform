"""冲压工艺 / 冲次 / 加工费 / 零件价。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.llm.process_fee_analysis_repository import ProcessFeeAnalysisRepository
from app.repositories.llm.stamping_cost_analysis_repository import (
    StampingCostAnalysisRepository,
)
from app.repositories.llm.stamping_process_analysis_repository import (
    StampingProcessAnalysisRepository,
)
from app.repositories.llm.tonnage_price_analysis_repository import (
    TonnagePriceAnalysisRepository,
)
from app.schemas.llm.analysis_payload import (
    AnalysisResultLeafPayload,
    RiskPayload,
)
from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm._money import shift_month
from app.services.llm.analysis.shared.anomaly import build_stamping_risks
from app.services.llm.analysis.shared.compose import compose_result
from app.services.llm.analysis.shared.cost_driver import (
    build_stamping_drivers,
    build_stamping_mom_anomalies,
)
from app.services.llm.analysis.shared.cost_trend import build_stamping_trend
from app.services.llm.analysis.shared.period_discontinue import (
    build_period_discontinue,
    period_discontinue_risk_entry,
    should_attach_period_discontinue,
)
from app.services.llm.analysis.shared.period_missing_supplier import (
    build_period_missing_supplier,
    period_missing_supplier_risk_entry,
    should_attach_period_missing_supplier,
)
from app.services.llm.analysis.shared.result import AnalysisRunResult
from app.services.llm.analysis.shared.summary import build_stamping_summary
from app.services.llm.analysis.stamping.part_cost import build_stamping_cost_drilldown
from app.services.llm.analysis.stamping.process import (
    build_stamping_process_drilldown,
    build_stamping_process_drivers,
    build_stamping_process_summary,
)
from app.services.llm.analysis.stamping.process_fee import (
    build_process_fee_drilldown,
    build_process_fee_summary,
)
from app.services.llm.analysis.stamping.tonnage import (
    build_tonnage_price_drilldown,
    build_tonnage_price_summary,
)
from app.services.llm.comparison_basis import resolve_comparability
from app.services.llm.query.parser.subjects import asks_tailor_weld_fee


class StampingAnalysis:
    def __init__(self) -> None:
        self._stamping_process_repo = StampingProcessAnalysisRepository()
        self._tonnage_repo = TonnagePriceAnalysisRepository()
        self._process_fee_repo = ProcessFeeAnalysisRepository()
        self._stamping_repo = StampingCostAnalysisRepository()

    def _attach_period_discontinue(
        self,
        db: Session,
        query: AnalysisQuery,
        *,
        parts_result: dict[str, AnalysisResultLeafPayload],
        risk_payload: RiskPayload | None = None,
    ) -> None:
        if not should_attach_period_discontinue(
            analyses=list(query.analyses),
            asks_part_price=bool(query.asks_part_price),
            part_number=query.part_number(),
        ):
            return
        tr = query.time_range
        payload = build_period_discontinue(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
        )
        parts_result["period_discontinue"] = payload
        if risk_payload is not None:
            entry = period_discontinue_risk_entry(payload)
            if entry is not None:
                risks = risk_payload.get("risks")
                if isinstance(risks, list):
                    risks.append(entry)

    def _attach_period_missing_supplier(
        self,
        db: Session,
        query: AnalysisQuery,
        *,
        parts_result: dict[str, AnalysisResultLeafPayload],
        risk_payload: RiskPayload | None = None,
    ) -> None:
        if not should_attach_period_missing_supplier(
            analyses=list(query.analyses),
            asks_part_price=bool(query.asks_part_price),
            part_number=query.part_number(),
        ):
            return
        payload = build_period_missing_supplier(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
        )
        parts_result["period_missing_supplier"] = payload
        if risk_payload is not None:
            entry = period_missing_supplier_risk_entry(payload)
            if entry is not None:
                risks = risk_payload.get("risks")
                if isinstance(risks, list):
                    risks.append(entry)

    def run_stamping_process(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「冲压零件列表」#/stamping-parts（工艺主数据）。"""
        rows = self._stamping_process_repo.query_part_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            version=query.bom_version(),
            part_number=query.part_number(),
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"冲压工艺 {len(rows)} 个零件" if rows else "当前范围无冲压工艺数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}

        if "summary" in query.analyses:
            out.summary = build_stamping_process_summary(rows)

        if "drivers" in query.analyses:
            parts_result["drivers"] = build_stamping_process_drivers(rows)

        if "drilldown" in query.analyses:
            part_number = query.part_number() or ""
            part, processes = self._stamping_process_repo.query_process_details(
                db,
                part_number=part_number,
                location=query.location(),
                vehicle_model=query.vehicle_model(),
                version=query.bom_version(),
            )
            parts_result["drilldown"] = build_stamping_process_drilldown(
                part,
                processes,
                part_number=part_number,
            )

        out.result = compose_result(parts_result, default_kind="summary")
        out.evidence["stamping_process_rows"] = [
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "process_count": row.process_count,
                "max_tonnage": row.max_tonnage,
                "vehicle_model": row.vehicle_model,
                "version": row.version,
                "location": row.location,
                "is_tailor_welded": row.is_tailor_welded,
            }
            for row in rows[:50]
        ]
        return out

    def run_stamping_tonnage(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「冲次单价列表」#/stamping-tonnage。"""
        year = query.time_range.end_year
        tonnage = query.tonnage()
        rows = self._tonnage_repo.query_rows(
            db,
            location=query.location(),
            year=year,
            tonnage=tonnage,
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"冲次单价 {len(rows)} 条" if rows else "当前范围无冲次单价数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}

        if "summary" in query.analyses:
            out.summary = build_tonnage_price_summary(rows)

        if "drilldown" in query.analyses or tonnage is not None:
            parts_result["drilldown"] = build_tonnage_price_drilldown(rows, tonnage=tonnage)

        out.result = compose_result(parts_result, default_kind="summary")
        out.evidence["tonnage_price_rows"] = [
            {
                "location": row.location,
                "year": row.year,
                "tonnage": row.tonnage,
                "price_per_stroke": f"{row.price_per_stroke:.3f}",
                "audit_status": row.audit_status,
            }
            for row in rows[:50]
        ]
        return out

    def run_stamping_process_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「冲压加工费列表」#/stamping-process-fee。"""
        tr = query.time_range
        part_token = query.part_number() or ""
        location = query.location()
        vehicle_model = query.vehicle_model()
        version = query.bom_version()
        part_number = part_token or None
        rows = self._process_fee_repo.query_rows(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            start_year=tr.start_year,
            end_year=tr.end_year,
            part_number=part_number,
        )
        outside_query_window = False
        if part_token and not rows and asks_tailor_weld_fee(query.user_question):
            rows = self._process_fee_repo.query_rows(
                db,
                location=location,
                vehicle_model=vehicle_model,
                version=version,
                part_number=part_number,
            )
            outside_query_window = bool(rows)
        head = (
            self._process_fee_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        if outside_query_window:
            data_message = (
                f"查询窗口{tr.start_year}年没有该件冲压加工费，"
                f"下面是库里其它年份的 {len(rows)} 行；拼焊费看其它费用"
            )
        elif rows:
            data_message = f"冲压加工费 {len(rows)} 条"
        else:
            data_message = "当前范围无冲压加工费数据"
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=data_message,
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}

        if "summary" in query.analyses:
            out.summary = build_process_fee_summary(rows)

        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_process_fee_drilldown(
                rows,
                part_token=part_token,
                head=head,
                outside_query_window=outside_query_window,
                query_window_year=tr.end_year,
            )

        out.result = compose_result(parts_result, default_kind="summary")
        out.evidence["process_fee_rows"] = [
            {
                "year": row.year,
                "part_number": row.part_number,
                "part_name": row.part_name,
                "location": row.location,
                "is_tailor_welded": row.is_tailor_welded,
                "other_fee": (f"{row.other_fee:.3f}" if row.other_fee is not None else None),
                "final_processing_fee": (
                    f"{row.final_processing_fee:.3f}"
                    if row.final_processing_fee is not None
                    else None
                ),
                "processing_fee": (
                    f"{row.processing_fee:.3f}" if row.processing_fee is not None else None
                ),
                "audit_status": row.audit_status,
            }
            for row in rows[:50]
        ]
        return out

    def run_stamping_part(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「冲压零件价格列表」#/stamping-part-cost。"""
        tr = query.time_range
        peek_previous_month = query.time_range.month_span() == 1 and any(
            kind in query.analyses for kind in ("risk", "drivers", "trend")
        )
        start_year, start_month = tr.start_year, tr.start_month
        if peek_previous_month:
            start_year, start_month = shift_month(tr.start_year, tr.start_month, -1)
        rows = self._stamping_repo.query_part_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            start_year=start_year,
            start_month=start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            part_number=query.part_number(),
        )
        focus_rows = (
            [row for row in rows if row.year == tr.end_year and row.month == tr.end_month]
            if peek_previous_month
            else rows
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(focus_rows),
            data_message=(
                f"冲压零件 {len(focus_rows)} 条" if focus_rows else "当前范围无冲压零件价格数据"
            ),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}

        if "summary" in query.analyses:
            out.summary = build_stamping_summary(focus_rows)

        if "trend" in query.analyses:
            parts_result["trend"] = build_stamping_trend(rows, basis=query.comparison_basis)

        if "drivers" in query.analyses:
            parts_result["drivers"] = build_stamping_drivers(rows)

        if "risk" in query.analyses:
            risk_payload = build_stamping_risks(focus_rows)
            self._attach_period_discontinue(
                db, query, parts_result=parts_result, risk_payload=risk_payload
            )
            self._attach_period_missing_supplier(
                db, query, parts_result=parts_result, risk_payload=risk_payload
            )
            parts_result["risk"] = risk_payload

        if rows and any(kind in query.analyses for kind in ("risk", "drivers", "trend")):
            focus_month = None
            if peek_previous_month:
                focus_month = f"{tr.end_year:04d}-{tr.end_month:02d}"
            parts_result["mom_anomalies"] = build_stamping_mom_anomalies(
                rows,
                focus_month=focus_month,
            )

        if "drilldown" in query.analyses:
            parts_result["drilldown"] = build_stamping_cost_drilldown(
                focus_rows, part_number=query.part_number() or ""
            )

        if "risk" not in query.analyses:
            self._attach_period_discontinue(db, query, parts_result=parts_result)
            self._attach_period_missing_supplier(db, query, parts_result=parts_result)

        out.result = compose_result(parts_result, default_kind="summary")
        out.evidence["stamping_part_rows"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "part_number": row.part_number,
                "part_name": row.part_name,
                "unit_cost": str(row.unit_cost),
                "calc_status": row.calc_status,
                "stamping_supplier": row.stamping_supplier,
            }
            for row in focus_rows[:50]
        ]
        return out
