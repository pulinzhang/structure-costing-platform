"""按 analyses[] 组合执行：Repository 查 → Analysis 算。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.llm.base_price_analysis_repository import BasePriceAnalysisRepository
from app.repositories.llm.cost_analysis_repository import (
    L0CostAnalysisRepository,
    L0PartPeriodRow,
)
from app.repositories.llm.policy_analysis_repository import PolicyAnalysisRepository
from app.repositories.llm.steel_price_analysis_repository import (
    SteelPriceAnalysisRepository,
)
from app.repositories.llm.scrap_price_analysis_repository import (
    ScrapPriceAnalysisRepository,
)
from app.common.part_number import part_numbers_match
from app.repositories.llm.stamping_cost_analysis_repository import (
    StampingCostAnalysisRepository,
    StampingPartPeriodRow,
)
from app.repositories.llm.stamping_process_analysis_repository import (
    StampingProcessAnalysisRepository,
)
from app.repositories.llm.process_fee_analysis_repository import (
    ProcessFeeAnalysisRepository,
)
from app.repositories.llm.tonnage_price_analysis_repository import (
    TonnagePriceAnalysisRepository,
)
from app.repositories.llm.annual_part_price_analysis_repository import (
    AnnualPartPriceAnalysisRepository,
)
from app.repositories.llm.packaging_transport_fee_analysis_repository import (
    PackagingTransportFeeAnalysisRepository,
)
from app.repositories.llm.l0_welding_fee_analysis_repository import (
    L0WeldingFeeAnalysisRepository,
)
from app.repositories.llm.bom_material_analysis_repository import (
    BomMaterialAnalysisRepository,
)
from app.repositories.llm.welding_process_breakdown_analysis_repository import (
    WeldingProcessBreakdownAnalysisRepository,
)
from app.repositories.llm.welding_unit_price_analysis_repository import (
    WeldingUnitPriceAnalysisRepository,
)
from app.repositories.llm.winning_thickness_analysis_repository import (
    WinningThicknessAnalysisRepository,
)
from app.services.llm._money import money_str
from app.services.llm.analysis.anomaly import build_risks, build_stamping_risks
from app.services.llm.analysis.comparison import build_location_comparison
from app.services.llm.analysis.cost_driver import (
    build_l0_drivers,
    build_l0_mom_anomalies,
    build_stamping_drivers,
)
from app.services.llm.analysis.cost_trend import (
    build_cost_trend,
    build_steel_trend,
    build_stamping_trend,
)
from app.services.llm.analysis.drilldown import build_drilldown
from app.services.llm.analysis.base_price_summary import (
    build_base_price_drivers,
    build_base_price_mom_anomalies,
    build_base_price_summary,
    build_base_price_trend,
)
from app.services.llm.analysis.process_fee_summary import (
    build_process_fee_drilldown,
    build_process_fee_summary,
)
from app.services.llm.analysis.part_lookup import (
    build_part_existence,
    build_part_lookup_summary,
    format_part_lookup_message,
    resolve_part_data_profile,
)
from app.services.llm.analysis.policy_summary import (
    build_policy_drivers,
    build_policy_mom_anomalies,
    build_policy_summary,
    build_policy_trend,
)
from app.services.llm.analysis.scrap_price_summary import (
    build_scrap_price_drivers,
    build_scrap_price_summary,
)
from app.services.llm.analysis.stamping_process_summary import (
    build_stamping_process_drilldown,
    build_stamping_process_drivers,
    build_stamping_process_summary,
)
from app.services.llm.analysis.summary import (
    build_stamping_summary,
    build_steel_summary,
    build_summary,
)
from app.services.llm.analysis.tonnage_price_summary import (
    build_tonnage_price_drilldown,
    build_tonnage_price_summary,
)
from app.services.llm.analysis.packaging_transport_fee_summary import (
    build_packaging_transport_fee_comparison,
    build_packaging_transport_fee_drilldown,
    build_packaging_transport_fee_drivers,
    build_packaging_transport_fee_summary,
)
from app.services.llm.analysis.annual_part_price_summary import (
    build_annual_part_price_comparison,
    build_annual_part_price_drilldown,
    build_annual_part_price_drivers,
    build_annual_part_price_summary,
)
from app.services.llm.analysis.welding_unit_price_summary import (
    build_welding_unit_price_comparison,
    build_welding_unit_price_drivers,
    build_welding_unit_price_summary,
)
from app.services.llm.analysis.bom_material_summary import (
    build_bom_material_drilldown,
    build_bom_material_drivers,
    build_bom_material_summary,
)
from app.services.llm.analysis.welding_process_breakdown_summary import (
    build_welding_breakdown_drilldown,
    build_welding_breakdown_drivers,
    build_welding_breakdown_summary,
)
from app.services.llm.analysis.l0_welding_fee_summary import (
    build_l0_welding_fee_comparison,
    build_l0_welding_fee_drilldown,
    build_l0_welding_fee_drivers,
    build_l0_welding_fee_summary,
)
from app.services.llm.analysis.winning_thickness_summary import (
    build_winning_thickness_drivers,
    build_winning_thickness_summary,
)
from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm.menu_catalog import expand_base_price_location
from app.services.llm.analysis._formulas import format_missing_price_message
from app.services.llm.analysis.comparability import resolve_runtime_comparability
from app.services.llm.analysis.constants import ANALYSIS_VERSION
from app.services.llm.query.comparison_basis import resolve_comparability


@dataclass
class AnalysisRunResult:
    summary: dict[str, Any] | None = None
    result: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    has_data: bool = False
    data_message: str = ""
    comparability: str = "unknown"
    comparability_note: str | None = None
    anomaly_note: str | None = None
    analysis_version: str = ANALYSIS_VERSION
    filtered_missing_price_count: int = 0


class AnalysisRunner:
    def __init__(self) -> None:
        self._l0_repo = L0CostAnalysisRepository()
        self._steel_repo = SteelPriceAnalysisRepository()
        self._stamping_repo = StampingCostAnalysisRepository()
        self._stamping_process_repo = StampingProcessAnalysisRepository()
        self._policy_repo = PolicyAnalysisRepository()
        self._base_price_repo = BasePriceAnalysisRepository()
        self._winning_thickness_repo = WinningThicknessAnalysisRepository()
        self._scrap_price_repo = ScrapPriceAnalysisRepository()
        self._tonnage_repo = TonnagePriceAnalysisRepository()
        self._process_fee_repo = ProcessFeeAnalysisRepository()
        self._welding_unit_price_repo = WeldingUnitPriceAnalysisRepository()
        self._annual_part_price_repo = AnnualPartPriceAnalysisRepository()
        self._packaging_transport_fee_repo = PackagingTransportFeeAnalysisRepository()
        self._bom_material_repo = BomMaterialAnalysisRepository()
        self._welding_breakdown_repo = WeldingProcessBreakdownAnalysisRepository()
        self._l0_welding_fee_repo = L0WeldingFeeAnalysisRepository()

    def run(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        if query.subject == "stamping_process":
            return self._run_stamping_process(db, query)
        if query.subject == "stamping_tonnage":
            return self._run_stamping_tonnage(db, query)
        if query.subject == "stamping_process_fee":
            return self._run_stamping_process_fee(db, query)
        if query.subject == "stamping_part":
            return self._run_stamping_part(db, query)
        if query.subject == "steel_price_policy":
            return self._run_steel_price_policy(db, query)
        if query.subject == "steel_base_price":
            return self._run_steel_base_price(db, query)
        if query.subject == "winning_thickness":
            return self._run_winning_thickness(db, query)
        if query.subject == "scrap_price":
            return self._run_scrap_price(db, query)
        if query.subject == "welding_unit_price":
            return self._run_welding_unit_price(db, query)
        if query.subject == "annual_part_price":
            return self._run_annual_part_price(db, query)
        if query.subject == "packaging_transport_fee":
            return self._run_packaging_transport_fee(db, query)
        if query.subject == "bom_material":
            return self._run_bom_material(db, query)
        if query.subject == "welding_process_breakdown":
            return self._run_welding_process_breakdown(db, query)
        if query.subject == "l0_welding_fee":
            return self._run_l0_welding_fee(db, query)
        if query.subject == "steel_price":
            return self._run_steel(db, query)
        if query.subject == "part":
            return self._run_part_lookup(db, query)
        return self._run_l0(db, query)

    def _run_stamping_process(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
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
            data_message=(f"冲压工艺零件={len(rows)}" if rows else "当前范围无冲压工艺数据"),
        )
        parts_result: dict[str, Any] = {}

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

        out.result = _compose_result(parts_result, default_kind="summary")
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

    def _run_stamping_tonnage(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
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
            data_message=(f"冲次单价行={len(rows)}" if rows else "当前范围无冲次单价数据"),
        )
        parts_result: dict[str, Any] = {}

        if "summary" in query.analyses:
            out.summary = build_tonnage_price_summary(rows)

        if "drilldown" in query.analyses or tonnage is not None:
            parts_result["drilldown"] = build_tonnage_price_drilldown(rows, tonnage=tonnage)

        out.result = _compose_result(parts_result, default_kind="summary")
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

    def _run_stamping_process_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「冲压加工费列表」#/stamping-process-fee。"""
        tr = query.time_range
        part_token = query.part_number() or ""
        rows = self._process_fee_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            version=query.bom_version(),
            start_year=tr.start_year,
            end_year=tr.end_year,
            part_number=part_token or None,
        )
        head = (
            self._process_fee_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"冲压加工费行={len(rows)}" if rows else "当前范围无冲压加工费数据"),
        )
        parts_result: dict[str, Any] = {}

        if "summary" in query.analyses:
            out.summary = build_process_fee_summary(rows)

        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_process_fee_drilldown(
                rows,
                part_token=part_token,
                head=head,
            )

        out.result = _compose_result(parts_result, default_kind="summary")
        out.evidence["process_fee_rows"] = [
            {
                "year": row.year,
                "part_number": row.part_number,
                "part_name": row.part_name,
                "location": row.location,
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

    def _run_stamping_part(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「冲压零件价格一览」#/stamping-part-cost。"""
        tr = query.time_range
        rows = self._stamping_repo.query_part_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            part_number=query.part_number(),
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"冲压零件行={len(rows)}" if rows else "当前范围无冲压零件价格数据"),
        )
        parts_result: dict[str, Any] = {}

        if "summary" in query.analyses:
            out.summary = build_stamping_summary(rows)

        if "trend" in query.analyses:
            parts_result["trend"] = build_stamping_trend(rows, basis=query.comparison_basis)

        if "drivers" in query.analyses:
            parts_result["drivers"] = build_stamping_drivers(rows)

        if "risk" in query.analyses:
            parts_result["risk"] = build_stamping_risks(rows)

        if "drilldown" in query.analyses:
            parts_result["drilldown"] = _build_stamping_drilldown(
                rows, part_number=query.part_number() or ""
            )

        out.result = _compose_result(parts_result, default_kind="summary")
        out.evidence["stamping_part_rows"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "part_number": row.part_number,
                "part_name": row.part_name,
                "unit_cost": str(row.unit_cost),
                "calc_status": row.calc_status,
                "stamping_supplier": row.stamping_supplier,
            }
            for row in rows[:50]
        ]
        return out

    def _run_steel_price_policy(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「加减价政策列表」#/steel-price-policy-download。"""
        tr = query.time_range
        policy_type = query.filter_get("policy_type")
        rows = self._policy_repo.query_ladder_rows(
            db,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            steel_mill=query.filter_get("steel_mill"),
            category_name=query.filter_get("category_name"),
            policy_type=policy_type,
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"加减价阶梯行={len(rows)}" if rows else "当前范围无加减价政策数据"),
        )
        parts_result: dict[str, Any] = {}
        if "summary" in query.analyses:
            out.summary = build_policy_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_policy_drivers(rows)
        if "trend" in query.analyses and rows:
            parts_result["trend"] = build_policy_trend(rows, basis=query.comparison_basis)
        if rows and query.time_range.month_span() > 1:
            parts_result["policy_anomalies"] = build_policy_mom_anomalies(rows)
        out.result = _compose_result(parts_result, default_kind="summary")
        out.evidence["policy_ladder_rows"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "steel_mill": row.steel_mill,
                "category_name": row.category_name,
                "policy_type": row.policy_type,
                "grade_value": row.grade_value,
                "price_adjustment": row.price_adjustment,
                "thick_min": str(row.thick_min) if row.thick_min is not None else None,
                "thick_max": str(row.thick_max) if row.thick_max is not None else None,
            }
            for row in rows[:50]
        ]
        return out

    def _run_steel_base_price(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「基准价格列表」#/base-price-download。"""
        tr = query.time_range
        rows = self._base_price_repo.query_rows(
            db,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            location=query.location(),
            steel_mill=query.filter_get("steel_mill"),
            category_name=query.filter_get("category_name"),
            grade=query.filter_get("grade"),
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"基准价行={len(rows)}" if rows else "当前范围无基准价格数据"),
        )
        parts_result: dict[str, Any] = {}
        if "summary" in query.analyses:
            out.summary = build_base_price_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_base_price_drivers(rows)
        if "trend" in query.analyses and rows:
            parts_result["trend"] = build_base_price_trend(rows, basis=query.comparison_basis)
        if rows and query.time_range.month_span() > 1:
            parts_result["base_price_anomalies"] = build_base_price_mom_anomalies(rows)
        out.result = _compose_result(parts_result, default_kind="summary")
        out.evidence["base_price_rows"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "location": row.location,
                "steel_mill": row.steel_mill,
                "grade": row.grade,
                "spec": row.spec,
                "base_price": money_str(row.base_price),
            }
            for row in rows[:50]
        ]
        return out

    def _run_winning_thickness(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「中标钢厂厚度价格一览表」#/winning-thickness-download。"""
        tr = query.time_range
        location = expand_base_price_location(query.location() or "")
        if not location:
            return AnalysisRunResult(
                comparability=resolve_comparability(query.comparison_basis),
                has_data=False,
                data_message="中标厚度价须指定基地",
            )

        rows = self._winning_thickness_repo.query_rows(
            db,
            year=tr.end_year,
            month=tr.end_month,
            location=location,
            steel_mill=query.filter_get("steel_mill"),
            category_name=query.filter_get("category_name"),
            grade=query.filter_get("grade"),
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"中标厚度价行={len(rows)}" if rows else "当前范围无中标厚度价数据"),
        )
        parts_result: dict[str, Any] = {}
        if "summary" in query.analyses:
            out.summary = build_winning_thickness_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_winning_thickness_drivers(rows)
        out.result = _compose_result(parts_result, default_kind="summary")
        out.evidence["winning_thickness_rows"] = [
            {
                "steel_mill": row.steel_mill,
                "category_name": row.category_name,
                "grade": row.grade,
                "thickness_range": row.thickness_range,
                "final_price": money_str(row.final_price),
            }
            for row in rows[:50]
        ]
        return out

    def _run_scrap_price(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「废料月度销售价」#/scrap-price。"""
        tr = query.time_range
        rows = self._scrap_price_repo.query_rows(
            db,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            location=query.location(),
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"废料价行={len(rows)}" if rows else "当前范围无废料销售价数据"),
        )
        parts_result: dict[str, Any] = {}
        if "summary" in query.analyses:
            out.summary = build_scrap_price_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_scrap_price_drivers(rows)
        out.result = _compose_result(parts_result, default_kind="summary")
        out.evidence["scrap_price_rows"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "location": row.location,
                "net_price": f"{row.net_price:.2f}",
                "market_price": f"{row.market_price:.2f}",
            }
            for row in rows[:50]
        ]
        return out

    def _run_welding_unit_price(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「焊接单价列表」#/bom-welding-unit-price。"""
        tr = query.time_range
        rows = self._welding_unit_price_repo.query_rows(
            db,
            location=query.location(),
            start_year=tr.start_year,
            end_year=tr.end_year,
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"焊接单价行={len(rows)}" if rows else "当前范围无焊接单价数据"),
        )
        parts_result: dict[str, Any] = {}

        if "summary" in query.analyses:
            out.summary = build_welding_unit_price_summary(rows)

        if "comparison" in query.analyses:
            parts_result["comparison"] = build_welding_unit_price_comparison(
                rows,
                location=query.location(),
            )

        if "drivers" in query.analyses:
            parts_result["drivers"] = build_welding_unit_price_drivers(rows)

        default_kind = "comparison" if "comparison" in query.analyses else "summary"
        out.result = _compose_result(parts_result, default_kind=default_kind)
        out.evidence["welding_unit_price_rows"] = [
            {
                "year": row.year,
                "location": row.location,
                "item_name": row.item_name,
                "unit": row.unit,
                "unit_price": f"{row.unit_price:.4f}",
                "audit_status": row.audit_status,
            }
            for row in rows[:50]
        ]
        return out

    def _run_annual_part_price(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「年度零件价列表」#/bom-annual-part-price（外购 + 一口价）。"""
        tr = query.time_range
        part_token = query.part_number() or ""
        rows = self._annual_part_price_repo.query_rows(
            db,
            location=query.location(),
            start_year=tr.start_year,
            end_year=tr.end_year,
            part_number=part_token or None,
        )
        if not rows and part_token:
            rows = self._annual_part_price_repo.query_rows(
                db,
                location=query.location(),
                part_number=part_token,
            )
        head = (
            self._annual_part_price_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"年度零件价行={len(rows)}" if rows else "当前范围无年度零件价数据"),
        )
        parts_result: dict[str, Any] = {}

        if "summary" in query.analyses:
            out.summary = build_annual_part_price_summary(rows)

        if "comparison" in query.analyses:
            parts_result["comparison"] = build_annual_part_price_comparison(
                rows,
                location=query.location(),
            )

        if "drivers" in query.analyses:
            parts_result["drivers"] = build_annual_part_price_drivers(rows)

        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_annual_part_price_drilldown(
                rows,
                part_token=part_token,
                head=head,
            )

        if "comparison" in query.analyses:
            default_kind = "comparison"
        elif part_token:
            default_kind = "drilldown"
        else:
            default_kind = "summary"
        out.result = _compose_result(parts_result, default_kind=default_kind)
        out.evidence["annual_part_price_rows"] = [
            {
                "year": row.year,
                "location": row.location,
                "part_number": row.part_number,
                "part_name": row.part_name,
                "supply_type": row.supply_type,
                "unit_price": f"{row.unit_price:.4f}",
                "audit_status": row.audit_status,
            }
            for row in rows[:50]
        ]
        return out

    def _run_packaging_transport_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「包装运输费列表」#/bom-packaging-transport-fee。"""
        tr = query.time_range
        part_token = query.part_number() or ""
        rows = self._packaging_transport_fee_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            start_year=tr.start_year,
            end_year=tr.end_year,
            part_number=part_token or None,
        )
        if not rows and part_token:
            rows = self._packaging_transport_fee_repo.query_rows(
                db,
                location=query.location(),
                vehicle_model=query.vehicle_model(),
                part_number=part_token,
            )
        head = (
            self._packaging_transport_fee_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"包装运输费行={len(rows)}" if rows else "当前范围无包装运输费数据"),
        )
        parts_result: dict[str, Any] = {}

        if "summary" in query.analyses:
            out.summary = build_packaging_transport_fee_summary(rows)

        if "comparison" in query.analyses:
            parts_result["comparison"] = build_packaging_transport_fee_comparison(
                rows,
                location=query.location(),
            )

        if "drivers" in query.analyses:
            parts_result["drivers"] = build_packaging_transport_fee_drivers(rows)

        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_packaging_transport_fee_drilldown(
                rows,
                part_token=part_token,
                head=head,
            )

        if "comparison" in query.analyses:
            default_kind = "comparison"
        elif part_token:
            default_kind = "drilldown"
        else:
            default_kind = "summary"
        out.result = _compose_result(parts_result, default_kind=default_kind)
        out.evidence["packaging_transport_fee_rows"] = [
            {
                "year": row.year,
                "location": row.location,
                "vehicle_model": row.vehicle_model,
                "part_number": row.part_number,
                "part_name": row.part_name,
                "packaging_transport_total": f"{row.packaging_transport_total:.4f}",
                "audit_status": row.audit_status,
            }
            for row in rows[:50]
        ]
        return out

    def _run_bom_material(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「材料清单列表」#/bom-material（产品结构/结构图同数据）。"""
        part_token = query.part_number() or ""
        rows = self._bom_material_repo.query_node_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
            part_number=part_token or None,
        )
        head = (
            self._bom_material_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"材料清单节点={len(rows)}" if rows else "当前范围无材料清单数据"),
        )
        parts_result: dict[str, Any] = {}
        if "summary" in query.analyses:
            out.summary = build_bom_material_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_bom_material_drivers(rows)
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_bom_material_drilldown(
                rows,
                part_token=part_token,
                head=head,
            )
        default_kind = "drilldown" if part_token else "summary"
        out.result = _compose_result(parts_result, default_kind=default_kind)
        out.evidence["bom_material_rows"] = [
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "level": row.level,
                "node_role": row.node_role,
                "location": row.location,
                "vehicle_model": row.vehicle_model,
                "bom_version": row.bom_version,
            }
            for row in rows[:50]
        ]
        return out

    def _run_welding_process_breakdown(
        self, db: Session, query: AnalysisQuery
    ) -> AnalysisRunResult:
        """对齐「焊接工艺拆解列表」#/bom-welding-process-breakdown-list。"""
        part_token = query.part_number() or ""
        rows = self._welding_breakdown_repo.query_node_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
            part_number=part_token or None,
        )
        head = (
            self._welding_breakdown_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(
                f"焊接工艺拆解节点={len(rows)}" if rows else "当前范围无焊接工艺拆解数据"
            ),
        )
        parts_result: dict[str, Any] = {}
        if "summary" in query.analyses:
            out.summary = build_welding_breakdown_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_welding_breakdown_drivers(rows)
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_welding_breakdown_drilldown(
                rows,
                part_token=part_token,
                head=head,
            )
        default_kind = "drilldown" if part_token else "summary"
        out.result = _compose_result(parts_result, default_kind=default_kind)
        out.evidence["welding_breakdown_rows"] = [
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "process_line_count": row.process_line_count,
                "location": row.location,
                "vehicle_model": row.vehicle_model,
                "bom_version": row.bom_version,
            }
            for row in rows[:50]
        ]
        return out

    def _run_l0_welding_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「成品焊接费列表」#/bom-l0-welding-fee-list。"""
        tr = query.time_range
        part_token = query.part_number() or ""
        rows = self._l0_welding_fee_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
            start_year=tr.start_year,
            end_year=tr.end_year,
            part_number=part_token or None,
        )
        if not rows and part_token:
            rows = self._l0_welding_fee_repo.query_rows(
                db,
                location=query.location(),
                vehicle_model=query.vehicle_model(),
                bom_version=query.bom_version(),
                part_number=part_token,
            )
        head = (
            self._l0_welding_fee_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"成品焊接费行={len(rows)}" if rows else "当前范围无成品焊接费数据"),
        )
        parts_result: dict[str, Any] = {}
        if "summary" in query.analyses:
            out.summary = build_l0_welding_fee_summary(rows)
        if "comparison" in query.analyses:
            parts_result["comparison"] = build_l0_welding_fee_comparison(
                rows,
                location=query.location(),
            )
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_l0_welding_fee_drivers(rows)
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_l0_welding_fee_drilldown(
                rows,
                part_token=part_token,
                head=head,
            )
        if "comparison" in query.analyses:
            default_kind = "comparison"
        elif part_token:
            default_kind = "drilldown"
        else:
            default_kind = "summary"
        out.result = _compose_result(parts_result, default_kind=default_kind)
        out.evidence["l0_welding_fee_rows"] = [
            {
                "year": row.year,
                "part_number": row.part_number,
                "part_name": row.part_name,
                "final_l0_welding_fee": (
                    f"{(row.final_l0_welding_fee or row.total_l0_welding_fee):.4f}"
                ),
                "calc_status": row.calc_status,
            }
            for row in rows[:50]
        ]
        return out

    def _run_steel(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        tr = query.time_range
        location = query.location()
        steel_rows = self._steel_repo.query_monthly_avg(
            db,
            location=location,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(steel_rows),
            data_message=f"钢材月度均价点数={len(steel_rows)}",
        )
        parts_result: dict[str, Any] = {}
        if "summary" in query.analyses:
            out.summary = build_steel_summary(steel_rows)
        if "trend" in query.analyses:
            parts_result["trend"] = build_steel_trend(steel_rows, basis=query.comparison_basis)
        default_kind = "trend" if "trend" in query.analyses else "summary"
        out.result = _compose_result(parts_result, default_kind=default_kind)
        out.evidence["steel_series"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "avg_final_price": str(row.avg_final_price),
                "row_count": row.row_count,
            }
            for row in steel_rows
        ]
        return out

    def _run_part_lookup(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """指定零件号：同时在 L0、冲压价、冲压工艺中检索。"""
        tr = query.time_range
        part_token = query.part_number() or ""
        l0_rows = self._l0_repo.query_part_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            part_number=part_token or None,
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
                parts_result["l0_drilldown"] = build_drilldown(l0_rows, part_number=part_token)
            if profile.stamping_cost_applicable:
                parts_result["stamping_cost_drilldown"] = _build_stamping_drilldown(
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

        out.result = _compose_result(parts_result, default_kind="part_existence")
        out.evidence["part_lookup"] = {
            "l0_rows": len(l0_rows),
            "stamping_cost_rows": len(stamping_rows),
            "stamping_process_rows": len(process_rows),
        }
        return out

    def _run_l0(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
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
        part_rows: list[L0PartPeriodRow] = []
        filtered_missing = 0
        if need_parts:
            part_rows = self._l0_repo.query_part_rows(
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

        comparability, comparability_note = resolve_runtime_comparability(
            basis=query.comparison_basis,
            part_rows=part_rows,
        )
        out = AnalysisRunResult(
            comparability=comparability,
            comparability_note=comparability_note,
            filtered_missing_price_count=filtered_missing,
        )
        parts_result: dict[str, Any] = {}
        driver_top_n = query.top_n()

        if "summary" in query.analyses:
            out.summary = build_summary(monthly, part_rows=part_rows or None)

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
            parts_result["risk"] = build_risks(
                part_rows,
                filtered_missing_price_count=filtered_missing,
            )

        if part_rows and any(kind in query.analyses for kind in ("risk", "drivers", "trend")):
            parts_result["mom_anomalies"] = build_l0_mom_anomalies(part_rows)

        if "drilldown" in query.analyses:
            part_number = query.part_number() or ""
            parts_result["drilldown"] = build_drilldown(part_rows, part_number=part_number)

        out.result = _compose_result(parts_result, default_kind="summary")
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
            out.summary = build_summary(monthly, part_rows=part_rows or None)

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


def _compose_result(parts_result: dict[str, Any], *, default_kind: str) -> dict[str, Any]:
    if len(parts_result) == 1:
        return next(iter(parts_result.values()))
    if parts_result:
        return {"kind": "composite", "parts": parts_result}
    return {"kind": default_kind}


def _build_stamping_drilldown(
    rows: list[StampingPartPeriodRow],
    *,
    part_number: str,
) -> dict[str, Any]:
    matched = (
        [row for row in rows if part_numbers_match(row.part_number, part_number)]
        if part_number
        else rows
    )
    if not matched:
        return {
            "kind": "drilldown",
            "part_number": part_number,
            "found": False,
            "message": "未找到该冲压零件价格记录",
        }
    latest = sorted(matched, key=lambda row: (row.year, row.month))[-1]
    return {
        "kind": "drilldown",
        "part_number": latest.part_number,
        "found": True,
        "part_name": latest.part_name,
        "unit_cost": str(latest.unit_cost),
        "material_net_per_part": (
            str(latest.material_net_per_part) if latest.material_net_per_part is not None else None
        ),
        "process_fee_amount": (
            str(latest.process_fee_amount) if latest.process_fee_amount is not None else None
        ),
        "calc_status": latest.calc_status,
        "stamping_supplier": latest.stamping_supplier,
        "month": f"{latest.year:04d}-{latest.month:02d}",
    }
