"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

核价引擎 — DAG 串行编排（同进程调用子计算）。
execute：ensure_run → 阶段循环 → finalize。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.types.repository_types import SummaryJson
from app.repositories.costing.engine.costing_engine_run_repository import (
    CostingEngineRunRepository,
)
from app.schemas.vo.costing_engine_vo import CostingEngineAnnualItemVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.generate.service import (
    BomProcurementObjectGenerateService,
)
from app.services.bom.welding_fee.calc.orchestrator.orchestrator import (
    BomWeldingFeeCalcOrchestrator,
)
from app.services.bom.welding_process_breakdown.generate.service import (
    BomWeldingProcessBreakdownGenerateService,
)
from app.services.costing.assembly_cost.calc.orchestrator.orchestrator import (
    AssemblyCostCalcOrchestrator,
)
from app.services.costing.engine.orchestrator.persist import finalize_execute
from app.services.costing.engine.orchestrator.phases import execute_all_phases
from app.services.costing.engine.orchestrator.prep import ensure_run
from app.services.costing.engine.orchestrator.progress import ProgressFn, ProgressNotifier
from app.services.costing.engine.scope.discovery import DiscoveryResult
from app.services.costing.stamping_part_cost.calc.orchestrator.orchestrator import (
    StampingPartCostCalcOrchestrator,
)
from app.services.costing.steel_price.calc.orchestrator.orchestrator import (
    SteelPriceCalcOrchestrator,
)
from app.services.stamping.die_fee.calc.orchestrator.orchestrator import (
    StampingDieFeeCalcOrchestrator,
)
from app.services.stamping.process_fee.calc.orchestrator.orchestrator import (
    StampingProcessFeeCalcOrchestrator,
)


class RunOrchestrator:
    """Phase3 年度补算 + Phase4 月度主链。"""

    def __init__(self) -> None:
        self.run_repo = CostingEngineRunRepository()
        self.process_fee_orch = StampingProcessFeeCalcOrchestrator()
        self.die_fee_orch = StampingDieFeeCalcOrchestrator()
        self.procurement_svc = BomProcurementObjectGenerateService()
        self.breakdown_svc = BomWeldingProcessBreakdownGenerateService()
        self.welding_orch = BomWeldingFeeCalcOrchestrator()
        self.steel_orch = SteelPriceCalcOrchestrator()
        self.part_cost_orch = StampingPartCostCalcOrchestrator()
        self.assembly_orch = AssemblyCostCalcOrchestrator()

    def execute(
        self,
        db: Session,
        *,
        run_id: int,
        discovery: DiscoveryResult,
        annual_items: list[CostingEngineAnnualItemVO],
        current_user: UserVO,
        progress_callback: ProgressFn | None = None,
    ) -> SummaryJson:
        progress = ProgressNotifier(progress_callback)
        ensure_run(self.run_repo, db, run_id)
        progress.report_stage("gate_plan", 1, 1, "门禁已通过，开始执行")
        carry = execute_all_phases(
            self,
            db,
            run_id=run_id,
            discovery=discovery,
            annual_items=annual_items,
            current_user=current_user,
            progress=progress,
        )
        return finalize_execute(self.run_repo, db, run_id, discovery, carry, progress)
