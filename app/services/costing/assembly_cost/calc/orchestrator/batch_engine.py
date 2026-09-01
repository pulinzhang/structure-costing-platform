"""批量总成核价引擎：逐卡 rollup 并 SAVEPOINT 落库。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, audit_create
from app.common.timezone import now
from app.repositories.costing.assembly_cost.assembly_cost_repository import (
    AssemblyCostIndirectInsert,
    AssemblyCostItemInsert,
    AssemblyCostUpsertPayload,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.assembly_cost.calc.orchestrator.deps import AssemblyCalcDeps
from app.services.costing.assembly_cost.calc.orchestrator.prep import CalcPrepContext
from app.services.costing.assembly_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.assembly_cost.calc.process_log import MISSING_PART_LIMIT
from app.services.costing.assembly_cost.calc.rollup import FORMULA_VERSION, rollup_assembly

logger = logging.getLogger("service.costing.assembly_cost.calc")


@dataclass(slots=True)
class BatchCalcOutcome:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    ok_n: int = 0
    partial_n: int = 0
    failed_n: int = 0


class BatchCalculationEngine:
    def __init__(self, deps: AssemblyCalcDeps) -> None:
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
        total = len(ctx.subjects)
        progress.report(25, f"开始计算 {total} 张核价卡…")

        for index, root in enumerate(ctx.subjects, start=1):
            existing = self._deps.cost_repo.get_by_business_key(
                db,
                year=ctx.year,
                month=ctx.month,
                location=ctx.location,
                vehicle_model=ctx.vehicle_model,
                bom_version=ctx.bom_version,
                source_node_id=root.id,
            )
            if existing is not None and existing.audit_status == AUDIT_APPROVED:
                meta = ctx.subject_meta.get(root.id)
                ctx.log_builder.add_card(
                    part_number=root.part_number,
                    part_name=root.part_name,
                    level=root.level,
                    is_tree_root=root.parent_id is None,
                    object_kind=meta.object_kind if meta else None,
                    status="skipped",
                    message="已审核跳过",
                )
                outcome.skipped += 1
                progress.tick_parts(index, total)
                continue

            try:
                with db.begin_nested():
                    result = rollup_assembly(
                        root=root,
                        children_by_parent=ctx.children,
                        stamping_prices=ctx.stamping_prices,
                        annual_prices=ctx.annual_prices,
                        welding=ctx.welding_by_bom_node.get(root.id),
                        packaging=ctx.packaging_by_part.get(root.part_number),
                        rates=ctx.rates,
                        annual_suppliers=ctx.annual_suppliers,
                        conflicted_part_numbers=ctx.conflicted_part_numbers,
                        nodes_by_id=ctx.nodes_by_id,
                    )
                    calc_status: str = result.status
                    calc_message = None
                    if not result.identities_ok:
                        calc_status = "failed"
                        calc_message = "恒等式校验失败"
                    meta = ctx.subject_meta.get(root.id)
                    payload = AssemblyCostUpsertPayload(
                        year=ctx.year,
                        month=ctx.month,
                        location=ctx.location,
                        vehicle_model=ctx.vehicle_model,
                        bom_version=ctx.bom_version,
                        source_node_id=root.id,
                        level=root.level,
                        is_tree_root=root.parent_id is None,
                        parent_node_id=root.parent_id,
                        root_part_number=result.root_part_number,
                        root_part_name=result.root_part_name,
                        procurement_object_id=meta.procurement_object_id if meta else None,
                        object_kind=meta.object_kind if meta else None,
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
                        should_cost=result.should_cost,
                        vendor_quote=result.vendor_quote,
                        gap_amount=result.gap_amount,
                        vendor_name=result.vendor_name,
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
                        calc_status=calc_status,
                        missing_leaf_count=result.missing_leaf_count,
                        calc_message=calc_message,
                        formula_version=FORMULA_VERSION,
                        calculated_at=now(),
                        calc_batch_id=calc_batch_id,
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                        items=[
                            AssemblyCostItemInsert(
                                node_level=line.node_level,
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
                            AssemblyCostIndirectInsert(
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
                missing_parts = [
                    f"{line.part_number}（{line.match_hint or 'missing'}）"
                    for line in result.lines
                    if line.cost_source == "missing"
                ][:MISSING_PART_LIMIT]
                ctx.log_builder.add_card(
                    part_number=result.part_number,
                    part_name=result.part_name,
                    level=root.level,
                    is_tree_root=root.parent_id is None,
                    object_kind=meta.object_kind if meta else None,
                    status=calc_status,
                    should_cost=result.should_cost,
                    grand_total=result.grand_total,
                    material_amount=result.material_amount,
                    welding_amount=result.welding_amount,
                    missing_leaf_count=result.missing_leaf_count,
                    message=calc_message,
                    missing_parts=missing_parts,
                )
                if is_created:
                    outcome.created += 1
                else:
                    outcome.updated += 1
                if calc_status == "ok":
                    outcome.ok_n += 1
                elif calc_status == "failed":
                    outcome.failed_n += 1
                else:
                    outcome.partial_n += 1
            except Exception as exc:
                logger.exception("总成核价失败 %s: %s", root.part_number, exc)
                meta = ctx.subject_meta.get(root.id)
                ctx.log_builder.add_card(
                    part_number=root.part_number,
                    part_name=root.part_name,
                    level=root.level,
                    is_tree_root=root.parent_id is None,
                    object_kind=meta.object_kind if meta else None,
                    status="failed",
                    message=str(exc),
                )
                outcome.failed_n += 1

            progress.tick_parts(index, total)

        return outcome
