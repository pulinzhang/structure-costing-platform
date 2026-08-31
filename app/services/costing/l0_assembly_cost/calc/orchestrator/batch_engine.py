"""批量成品核价引擎：逐 L0 rollup 并 SAVEPOINT 落库。"""

from __future__ import annotations

from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, audit_create
from app.common.timezone import now
from app.repositories.costing.l0_assembly_cost.l0_assembly_cost_repository import (
    L0AssemblyCostIndirectInsert,
    L0AssemblyCostItemInsert,
    L0AssemblyCostUpsertPayload,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.l0_assembly_cost.calc.orchestrator.deps import L0AssemblyCalcDeps
from app.services.costing.l0_assembly_cost.calc.orchestrator.prep import CalcPrepContext
from app.services.costing.l0_assembly_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.l0_assembly_cost.calc.rollup import FORMULA_VERSION, rollup_l0

logger = logging.getLogger("service.costing.l0_assembly_cost.calc")


@dataclass(slots=True)
class BatchCalcOutcome:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    ok_n: int = 0
    partial_n: int = 0
    failed_n: int = 0


class BatchCalculationEngine:
    def __init__(self, deps: L0AssemblyCalcDeps) -> None:
        self._deps = deps

    def run(
        self,
        db: Session,
        *,
        ctx: CalcPrepContext,
        current_user: UserVO,
        calc_batch_id: str | None,
        progress: ProgressNotifier,
    ) -> BatchCalcOutcome:
        outcome = BatchCalcOutcome()
        audit = audit_create(current_user)
        total_l0 = len(ctx.l0_nodes)
        progress.report(25, f"开始计算 {total_l0} 个成品…")

        for index, l0 in enumerate(ctx.l0_nodes, start=1):
            existing = self._deps.cost_repo.get_by_business_key(
                db,
                year=ctx.year,
                month=ctx.month,
                location=ctx.location,
                vehicle_model=ctx.vehicle_model,
                bom_version=ctx.bom_version,
                part_number=l0.part_number,
            )
            if existing is not None and existing.audit_status == AUDIT_APPROVED:
                outcome.skipped += 1
                progress.tick_parts(index, total_l0)
                continue

            try:
                with db.begin_nested():
                    result = rollup_l0(
                        l0=l0,
                        children_by_parent=ctx.children,
                        stamping_prices=ctx.stamping_prices,
                        annual_prices=ctx.annual_prices,
                        welding=ctx.welding_by_part.get(l0.part_number),
                        packaging=ctx.packaging_by_part.get(l0.part_number),
                        rates=ctx.rates,
                    )
                    payload = L0AssemblyCostUpsertPayload(
                        year=ctx.year,
                        month=ctx.month,
                        location=ctx.location,
                        vehicle_model=ctx.vehicle_model,
                        bom_version=ctx.bom_version,
                        part_number=result.part_number,
                        part_name=result.part_name,
                        supply_qty=result.supply_qty,
                        bom_snapshot_id=ctx.snapshot_id,
                        sketch_url=result.sketch_url,
                        stamping_amount=result.stamping_amount,
                        purchased_amount=result.purchased_amount,
                        bundle_amount=result.bundle_amount,
                        material_amount=result.material_amount,
                        welding_amount=result.welding_amount,
                        welding_other_fee=result.welding_other_fee,
                        total_amount=result.total_amount,
                        unit_transport_fee=result.unit_transport_fee,
                        warehouse_bundling_fee=result.warehouse_bundling_fee,
                        finished_finance_fee=result.finished_finance_fee,
                        finished_management_fee=result.finished_management_fee,
                        finished_scrap_fee=result.finished_scrap_fee,
                        finished_pretax_profit_fee=result.finished_pretax_profit_fee,
                        gauge_alloc_fee=result.gauge_alloc_fee,
                        fixture_alloc_fee=result.fixture_alloc_fee,
                        allocation_fee_total=result.allocation_fee_total,
                        indirect_amount=result.indirect_amount,
                        grand_total=result.grand_total,
                        finance_rate=result.finance_rate,
                        management_rate=result.management_rate,
                        scrap_rate=result.scrap_rate,
                        pretax_profit_rate=result.pretax_profit_rate,
                        welding_fee_id=result.welding_fee_id,
                        welding_summary=result.welding_summary,
                        calc_status=result.status,
                        missing_leaf_count=result.missing_leaf_count,
                        calc_message=None,
                        formula_version=FORMULA_VERSION,
                        calculated_at=now(),
                        calc_batch_id=calc_batch_id,
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                        items=[
                            L0AssemblyCostItemInsert(
                                level_label=line.level_label,
                                bom_node_id=line.bom_node_id,
                                part_number=line.part_number,
                                part_name=line.part_name,
                                node_role=line.node_role,
                                supply_type=line.supply_type,
                                cost_source=line.cost_source,
                                match_hint=line.match_hint,
                                unit_price=line.unit_price,
                                effective_qty=line.effective_qty,
                                line_amount=line.line_amount,
                                sort_no=line.sort_no,
                            )
                            for line in result.lines
                        ],
                        indirects=[
                            L0AssemblyCostIndirectInsert(
                                code=ind.code,
                                label=ind.label,
                                amount=ind.amount,
                                rate=ind.rate,
                                base_amount=ind.base_amount,
                                sort_no=ind.sort_no,
                            )
                            for ind in result.indirect_lines
                        ],
                    )
                    _, is_created = self._deps.cost_repo.upsert_with_children(db, payload)
                if is_created:
                    outcome.created += 1
                else:
                    outcome.updated += 1
                if result.status == "ok":
                    outcome.ok_n += 1
                else:
                    outcome.partial_n += 1
            except Exception as exc:
                logger.exception("L0 核价失败 %s: %s", l0.part_number, exc)
                outcome.failed_n += 1

            progress.tick_parts(index, total_l0)

        return outcome
