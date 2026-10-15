"""年度零件价 / 包装运输费 / 材料清单。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.llm.annual_part_price_analysis_repository import (
    AnnualPartPriceAnalysisRepository,
)
from app.repositories.llm.bom_material_analysis_repository import (
    BomMaterialAnalysisRepository,
)
from app.repositories.llm.packaging_transport_fee_analysis_repository import (
    PackagingTransportFeeAnalysisRepository,
)
from app.schemas.llm.analysis_payload import (
    AnalysisResultLeafPayload,
    RiskPayload,
)
from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm.analysis.bom.annual_part_price import (
    annual_price_conversion_risk_entry,
    build_annual_part_price_comparison,
    build_annual_part_price_conversion_anomalies,
    build_annual_part_price_drilldown,
    build_annual_part_price_drivers,
    build_annual_part_price_summary,
)
from app.services.llm.analysis.bom.material import (
    build_bom_material_drilldown,
    build_bom_material_drivers,
    build_bom_material_summary,
)
from app.services.llm.analysis.bom.packaging_transport import (
    build_packaging_transport_fee_comparison,
    build_packaging_transport_fee_drilldown,
    build_packaging_transport_fee_drivers,
    build_packaging_transport_fee_summary,
)
from app.services.llm.analysis.shared.compose import compose_result
from app.services.llm.analysis.shared.result import AnalysisRunResult
from app.services.llm.analysis.shared.standard_part_price import (
    build_standard_part_price_anomalies,
    standard_part_price_risk_entry,
)
from app.services.llm.comparison_basis import resolve_comparability


class BomAnalysis:
    def __init__(self) -> None:
        self._annual_part_price_repo = AnnualPartPriceAnalysisRepository()
        self._packaging_transport_fee_repo = PackagingTransportFeeAnalysisRepository()
        self._bom_material_repo = BomMaterialAnalysisRepository()

    def run_annual_part_price(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
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
            data_message=(f"年度零件价 {len(rows)} 条" if rows else "当前范围无年度零件价数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}

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

        if "risk" in query.analyses:
            conversion = build_annual_part_price_conversion_anomalies(rows)
            standard = build_standard_part_price_anomalies(rows)
            parts_result["annual_price_anomalies"] = conversion
            parts_result["standard_part_anomalies"] = standard
            risk_payload: RiskPayload = {"kind": "risk", "risks": []}
            conversion_risk = annual_price_conversion_risk_entry(conversion)
            if conversion_risk is not None:
                risk_payload["risks"].append(conversion_risk)
                risk_payload["annual_price_conversion_count"] = conversion_risk["count"]
            standard_risk = standard_part_price_risk_entry(standard)
            if standard_risk is not None:
                risk_payload["risks"].append(standard_risk)
                risk_payload["standard_part_high_price_count"] = standard_risk["count"]
            parts_result["risk"] = risk_payload

        if "comparison" in query.analyses:
            default_kind = "comparison"
        elif part_token:
            default_kind = "drilldown"
        else:
            default_kind = "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        out.evidence["annual_part_price_rows"] = [
            {
                "year": row.year,
                "location": row.location,
                "part_number": row.part_number,
                "part_name": row.part_name,
                "supply_type": row.supply_type,
                "unit": row.unit,
                "unit_price": f"{row.unit_price:.4f}",
                "purchase_unit": row.purchase_unit,
                "purchase_unit_price": (
                    f"{row.purchase_unit_price:.4f}"
                    if row.purchase_unit_price is not None
                    else None
                ),
                "conversion_factor": str(row.conversion_factor),
                "audit_status": row.audit_status,
            }
            for row in rows[:50]
        ]
        return out

    def run_packaging_transport_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
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
            data_message=(f"包装运输费 {len(rows)} 条" if rows else "当前范围无包装运输费数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}

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
        out.result = compose_result(parts_result, default_kind=default_kind)
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

    def run_bom_material(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
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
            data_message=(f"材料清单 {len(rows)} 条" if rows else "当前范围无材料清单数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
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
        out.result = compose_result(parts_result, default_kind=default_kind)
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
