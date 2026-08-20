"""
成品月核价 — 计算编排器

职责：加载上游只读数据 → rollup 纯函数 → 持久化结果。
不写 SQL；审核行跳过覆盖。
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Callable

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, audit_create
from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.bom.annual_part_price import BomAnnualPartPrice
from app.models.bom.l0_welding_fee import BomL0WeldingFee
from app.models.bom.node import BomNode, BomSnapshot
from app.models.bom.packaging_transport_fee import BomPackagingTransportFee
from app.models.costing.stamping_part_cost import StampingPartCost
from app.repositories.costing.l0_assembly_cost.l0_assembly_cost_repository import (
    L0AssemblyCostIndirectInsert,
    L0AssemblyCostItemInsert,
    L0AssemblyCostRepository,
    L0AssemblyCostUpsertPayload,
)
from app.schemas.dto.l0_assembly_cost_dto import L0AssemblyCostCalcDTO
from app.schemas.vo.l0_assembly_cost_vo import (
    L0AssemblyCostCalcReadyVO,
    L0AssemblyCostCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.l0_assembly_cost.calc.calc_log_service import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    L0AssemblyCostCalcLogService,
    SCOPE_REQUIRED_MESSAGE,
)
from app.services.costing.l0_assembly_cost.calc.rollup import (
    FORMULA_VERSION,
    RollupBomNode,
    RollupFinishedRates,
    RollupPackagingFee,
    RollupWeldingFee,
    rollup_l0,
)
from app.services.settings.system.settings_service import SettingsService

logger = logging.getLogger("service.costing.l0_assembly_cost.calc")

ProgressCallback = Callable[[int, str], None]


class L0AssemblyCostCalcOrchestrator:
    """成品月核价计算编排。"""

    def __init__(self) -> None:
        self.cost_repo = L0AssemblyCostRepository()
        self.calc_log_service = L0AssemblyCostCalcLogService()
        self.settings_service = SettingsService()

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> L0AssemblyCostCalcReadyVO:
        location = location.strip()
        vehicle_model = vehicle_model.strip()
        bom_version = bom_version.strip()
        snap = (
            db.query(BomSnapshot)
            .filter(
                BomSnapshot.location == location,
                BomSnapshot.vehicle_model == vehicle_model,
                BomSnapshot.bom_version == bom_version,
            )
            .one_or_none()
        )
        l0_count = 0
        if snap is not None:
            l0_count = (
                db.query(BomNode)
                .filter(BomNode.snapshot_id == snap.id, BomNode.level == 0)
                .count()
            )
        stamping_n = (
            db.query(StampingPartCost)
            .filter(
                StampingPartCost.location == location,
                StampingPartCost.vehicle_model == vehicle_model,
                StampingPartCost.year == year,
                StampingPartCost.month == month,
                StampingPartCost.calc_status == "success",
                StampingPartCost.unit_cost.isnot(None),
            )
            .count()
        )
        annual_n = (
            db.query(BomAnnualPartPrice)
            .filter(
                BomAnnualPartPrice.location == location,
                BomAnnualPartPrice.year == year,
                BomAnnualPartPrice.unit_price.isnot(None),
            )
            .count()
        )
        weld_n = (
            db.query(BomL0WeldingFee)
            .filter(
                BomL0WeldingFee.location == location,
                BomL0WeldingFee.vehicle_model == vehicle_model,
                BomL0WeldingFee.year == year,
                BomL0WeldingFee.bom_version == bom_version,
            )
            .count()
        )
        pkg_n = (
            db.query(BomPackagingTransportFee)
            .filter(
                BomPackagingTransportFee.location == location,
                BomPackagingTransportFee.year == year,
            )
            .count()
        )
        ready = l0_count > 0 and (stamping_n > 0 or annual_n > 0)
        message = None
        if snap is None:
            message = "未找到对应 BOM 快照"
            ready = False
        elif l0_count == 0:
            message = "BOM 无 L0 成品"
            ready = False
        elif stamping_n == 0 and annual_n == 0:
            message = "无冲压价且无年度价，无法计算"
            ready = False
        return L0AssemblyCostCalcReadyVO(
            l0_count=l0_count,
            stamping_price_count=stamping_n,
            annual_price_count=annual_n,
            welding_fee_count=weld_n,
            packaging_fee_count=pkg_n,
            bom_version=bom_version,
            ready=ready,
            message=message,
        )

    def calculate(
        self,
        db: Session,
        dto: L0AssemblyCostCalcDTO,
        *,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> L0AssemblyCostCalcResultVO:
        year = dto.year
        month = dto.month
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        bom_version = dto.bom_version.strip()
        if not location or not vehicle_model or not bom_version:
            raise BusinessException(SCOPE_REQUIRED_MESSAGE)

        def report(progress: int, msg: str) -> None:
            if progress_callback is not None:
                progress_callback(progress, msg)

        report(5, "加载 BOM…")
        snap = (
            db.query(BomSnapshot)
            .filter(
                BomSnapshot.location == location,
                BomSnapshot.vehicle_model == vehicle_model,
                BomSnapshot.bom_version == bom_version,
            )
            .one_or_none()
        )
        if snap is None:
            raise BusinessException(f"无 BOM 快照: {location}/{vehicle_model}/{bom_version}")

        orm_nodes = db.query(BomNode).filter(BomNode.snapshot_id == snap.id).all()
        nodes = [
            RollupBomNode(
                id=n.id,
                parent_id=n.parent_id,
                level=int(n.level),
                part_number=n.part_number,
                part_name=n.part_name,
                qty=Decimal(str(n.qty if n.qty is not None else 1)),
                node_role=n.node_role,
                sort_no=n.sort_no or 0,
                sketch_url=getattr(n, "sketch_url", None),
            )
            for n in orm_nodes
        ]
        children: dict[int | None, list[RollupBomNode]] = {}
        for node in nodes:
            children.setdefault(node.parent_id, []).append(node)
        l0_nodes = sorted(
            [n for n in nodes if n.level == 0],
            key=lambda n: (n.sort_no, n.part_number),
        )
        if not l0_nodes:
            raise BusinessException("BOM 无 L0 成品节点")

        report(15, "加载上游价表…")
        stamping_prices = {
            r.part_number: Decimal(str(r.unit_cost))
            for r in db.query(StampingPartCost)
            .filter(
                StampingPartCost.location == location,
                StampingPartCost.vehicle_model == vehicle_model,
                StampingPartCost.year == year,
                StampingPartCost.month == month,
                StampingPartCost.calc_status == "success",
                StampingPartCost.unit_cost.isnot(None),
            )
            .all()
        }
        annual_prices = {
            r.part_number: Decimal(str(r.unit_price))
            for r in db.query(BomAnnualPartPrice)
            .filter(
                BomAnnualPartPrice.location == location,
                BomAnnualPartPrice.year == year,
                BomAnnualPartPrice.unit_price.isnot(None),
            )
            .all()
        }
        welding_by_part: dict[str, RollupWeldingFee] = {}
        for weld_row in (
            db.query(BomL0WeldingFee)
            .filter(
                BomL0WeldingFee.location == location,
                BomL0WeldingFee.vehicle_model == vehicle_model,
                BomL0WeldingFee.year == year,
                BomL0WeldingFee.bom_version == bom_version,
            )
            .all()
        ):
            final = weld_row.final_l0_welding_fee
            if final is None:
                final = weld_row.total_l0_welding_fee or Decimal("0")
            welding_by_part[weld_row.part_number] = RollupWeldingFee(
                final_amount=Decimal(str(final)),
                other_fee=Decimal(str(weld_row.other_fee or 0)),
                missing_price_count=int(weld_row.missing_price_count or 0),
                welding_fee_id=weld_row.id,
                summary=None,
            )
        packaging_by_part: dict[str, RollupPackagingFee] = {}
        for pkg_row in (
            db.query(BomPackagingTransportFee)
            .filter(
                BomPackagingTransportFee.location == location,
                BomPackagingTransportFee.year == year,
            )
            .all()
        ):
            packaging_by_part[pkg_row.part_number] = RollupPackagingFee(
                unit_transport_fee=Decimal(str(pkg_row.unit_transport_fee)),
                warehouse_bundling_fee=Decimal(str(pkg_row.other_fee or 0)),
            )

        rates = RollupFinishedRates(
            finance_rate=self.settings_service.get_finished_finance_rate(db),
            management_rate=self.settings_service.get_finished_management_rate(db),
            scrap_rate=self.settings_service.get_finished_scrap_rate(db),
            pretax_profit_rate=self.settings_service.get_finished_pretax_profit_rate(db),
        )
        audit = audit_create(current_user)

        created = 0
        updated = 0
        skipped = 0
        ok_n = 0
        partial_n = 0
        failed_n = 0
        total_l0 = len(l0_nodes)

        report(25, f"开始计算 {total_l0} 个成品…")
        for index, l0 in enumerate(l0_nodes, start=1):
            existing = self.cost_repo.get_by_business_key(
                db,
                year=year,
                month=month,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                part_number=l0.part_number,
            )
            if existing is not None and existing.audit_status == AUDIT_APPROVED:
                skipped += 1
                continue

            try:
                result = rollup_l0(
                    l0=l0,
                    children_by_parent=children,
                    stamping_prices=stamping_prices,
                    annual_prices=annual_prices,
                    welding=welding_by_part.get(l0.part_number),
                    packaging=packaging_by_part.get(l0.part_number),
                    rates=rates,
                )
                payload = L0AssemblyCostUpsertPayload(
                    year=year,
                    month=month,
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    part_number=result.part_number,
                    part_name=result.part_name,
                    supply_qty=result.supply_qty,
                    bom_snapshot_id=snap.id,
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
                _, is_created = self.cost_repo.upsert_with_children(db, payload)
                if is_created:
                    created += 1
                else:
                    updated += 1
                if result.status == "ok":
                    ok_n += 1
                else:
                    partial_n += 1
            except Exception as exc:  # noqa: BLE001 — 单件失败不中断整批
                logger.exception("L0 核价失败 %s: %s", l0.part_number, exc)
                failed_n += 1

            if index % 5 == 0 or index == total_l0:
                pct = 25 + int(70 * index / total_l0)
                report(pct, f"已处理 {index}/{total_l0}")

        db.commit()

        if failed_n > 0 and ok_n == 0 and partial_n == 0:
            status = STATUS_FAILED
        elif partial_n > 0 or failed_n > 0:
            status = STATUS_PARTIAL
        else:
            status = STATUS_SUCCESS
        message = (
            f"新增 {created}，更新 {updated}，跳过已审 {skipped}，"
            f"ok {ok_n}，partial {partial_n}，失败 {failed_n}"
        )
        if log_id is not None:
            self.calc_log_service.finalize(
                db,
                log_id=log_id,
                status=status,
                message=message,
                l0_total=total_l0,
                ok_count=ok_n,
                partial_count=partial_n,
                failed_count=failed_n,
                skipped_approved_count=skipped,
            )
        report(100, message)
        return L0AssemblyCostCalcResultVO(
            status=status,
            created_count=created,
            updated_count=updated,
            skipped_approved_count=skipped,
            ok_count=ok_n,
            partial_count=partial_n,
            failed_count=failed_n,
            message=message,
        )
