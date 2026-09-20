"""按 subject 分发到各主题 runner：Repository 查 → Analysis 算。"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm.analysis.assembly.run import AssemblyAnalysis
from app.services.llm.analysis.bom.run import BomAnalysis
from app.services.llm.analysis.ops.run import OpsAnalysis
from app.services.llm.analysis.shared.result import AnalysisRunResult
from app.services.llm.analysis.stamping.run import StampingAnalysis
from app.services.llm.analysis.steel.run import SteelAnalysis
from app.services.llm.analysis.welding.run import WeldingAnalysis

__all__ = ["AnalysisRunner", "AnalysisRunResult"]


class AnalysisRunner:
    """薄分发：只按 query.subject 交给对应主题类。"""

    def __init__(self) -> None:
        self._ops = OpsAnalysis()
        self._stamping = StampingAnalysis()
        self._steel = SteelAnalysis()
        self._welding = WeldingAnalysis()
        self._bom = BomAnalysis()
        self._assembly = AssemblyAnalysis()
        self._handlers: dict[str, Callable[[Session, AnalysisQuery], AnalysisRunResult]] = {
            "ops_workbench": self._ops.run_ops_workbench,
            "stamping_die_fee": self._ops.run_stamping_die_fee,
            "stamping_gauge_fee": self._ops.run_stamping_gauge_fee,
            "procurement_object": self._ops.run_procurement_object,
            "engineering_change": self._ops.run_engineering_change,
            "stamping_process": self._stamping.run_stamping_process,
            "stamping_tonnage": self._stamping.run_stamping_tonnage,
            "stamping_process_fee": self._stamping.run_stamping_process_fee,
            "stamping_part": self._stamping.run_stamping_part,
            "steel_price_policy": self._steel.run_steel_price_policy,
            "steel_base_price": self._steel.run_steel_base_price,
            "winning_thickness": self._steel.run_winning_thickness,
            "scrap_price": self._steel.run_scrap_price,
            "welding_unit_price": self._welding.run_welding_unit_price,
            "annual_part_price": self._bom.run_annual_part_price,
            "packaging_transport_fee": self._bom.run_packaging_transport_fee,
            "bom_material": self._bom.run_bom_material,
            "welding_process_breakdown": self._welding.run_welding_process_breakdown,
            "l0_welding_fee": self._welding.run_l0_welding_fee,
            "steel_price": self._steel.run_steel,
        }

    def run(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        handler = self._handlers.get(query.subject)
        if handler is not None:
            return handler(db, query)
        if query.subject == "part":
            return self._assembly.run_part(db, query)
        return self._assembly.run_default(db, query)
