"""管理者作业台：待审核 / 算不全件数（只读结果表）。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.bom.procurement_object import BomProcurementObject, BomProcurementObjectList
from app.models.bom.welding_fee import BomWeldingFee
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.stamping_part_cost import StampingPartCost
from app.models.stamping.die_fee import StampingDieFee
from app.repositories.llm.location_in import location_in_clause
from app.services.llm._money import ym_int


@dataclass(frozen=True, slots=True)
class WorkbenchBoardRow:
    slice_id: str
    label: str
    hash_page: str
    grain: str
    row_count: int
    pending_audit_count: int
    incomplete_count: int
    pending_confirm_count: int = 0


class OpsWorkbenchRepository:
    def query_boards(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        year: int,
        month: int,
    ) -> list[WorkbenchBoardRow]:
        return [
            self._assembly_board(
                db, location=location, vehicle_model=vehicle_model, year=year, month=month
            ),
            self._stamping_part_board(
                db, location=location, vehicle_model=vehicle_model, year=year, month=month
            ),
            self._welding_fee_board(db, location=location, vehicle_model=vehicle_model, year=year),
            self._die_fee_board(db, location=location, vehicle_model=vehicle_model, year=year),
            self._procurement_board(db, location=location, vehicle_model=vehicle_model),
        ]

    def _assembly_board(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        year: int,
        month: int,
    ) -> WorkbenchBoardRow:
        ym = ym_int(year, month)
        q = db.query(
            func.count(AssemblyCost.id),
            func.coalesce(
                func.sum(case((AssemblyCost.audit_status == "pending", 1), else_=0)),
                0,
            ),
            func.coalesce(func.sum(case((AssemblyCost.calc_status != "ok", 1), else_=0)), 0),
        ).filter(
            (AssemblyCost.year * 100 + AssemblyCost.month) == ym,
            AssemblyCost.is_tree_root.is_(True),
        )
        loc_filter = location_in_clause(db, AssemblyCost.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(AssemblyCost.vehicle_model == vehicle_model)
        total, pending, incomplete = q.one()
        return WorkbenchBoardRow(
            slice_id="assembly_cost",
            label="总成核价一览",
            hash_page="assembly-cost",
            grain="month",
            row_count=int(total or 0),
            pending_audit_count=int(pending or 0),
            incomplete_count=int(incomplete or 0),
        )

    def _stamping_part_board(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        year: int,
        month: int,
    ) -> WorkbenchBoardRow:
        ym = ym_int(year, month)
        q = db.query(
            func.count(StampingPartCost.id),
            func.coalesce(
                func.sum(case((StampingPartCost.audit_status == "pending", 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((StampingPartCost.calc_status != "success", 1), else_=0)),
                0,
            ),
        ).filter((StampingPartCost.year * 100 + StampingPartCost.month) == ym)
        loc_filter = location_in_clause(db, StampingPartCost.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(StampingPartCost.vehicle_model == vehicle_model)
        total, pending, incomplete = q.one()
        return WorkbenchBoardRow(
            slice_id="stamping_part",
            label="冲压零件价格一览",
            hash_page="stamping-part-cost",
            grain="month",
            row_count=int(total or 0),
            pending_audit_count=int(pending or 0),
            incomplete_count=int(incomplete or 0),
        )

    def _welding_fee_board(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        year: int,
    ) -> WorkbenchBoardRow:
        q = db.query(
            func.count(BomWeldingFee.id),
            func.coalesce(
                func.sum(case((BomWeldingFee.audit_status == "pending", 1), else_=0)),
                0,
            ),
            func.coalesce(func.sum(case((BomWeldingFee.calc_status != "ok", 1), else_=0)), 0),
        ).filter(BomWeldingFee.level == 0, BomWeldingFee.year == year)
        loc_filter = location_in_clause(db, BomWeldingFee.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(BomWeldingFee.vehicle_model == vehicle_model)
        total, pending, incomplete = q.one()
        return WorkbenchBoardRow(
            slice_id="l0_welding_fee",
            label="焊接费列表",
            hash_page="bom-welding-fee-list",
            grain="year",
            row_count=int(total or 0),
            pending_audit_count=int(pending or 0),
            incomplete_count=int(incomplete or 0),
        )

    def _die_fee_board(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        year: int,
    ) -> WorkbenchBoardRow:
        q = db.query(
            func.count(StampingDieFee.id),
            func.coalesce(
                func.sum(case((StampingDieFee.audit_status == "pending", 1), else_=0)),
                0,
            ),
            func.coalesce(func.sum(case((StampingDieFee.final_die_fee <= 0, 1), else_=0)), 0),
        ).filter(StampingDieFee.year == year)
        loc_filter = location_in_clause(db, StampingDieFee.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(StampingDieFee.vehicle_model == vehicle_model)
        total, pending, incomplete = q.one()
        return WorkbenchBoardRow(
            slice_id="stamping_die_fee",
            label="冲压模具费列表",
            hash_page="stamping-die-fee",
            grain="year",
            row_count=int(total or 0),
            pending_audit_count=int(pending or 0),
            incomplete_count=int(incomplete or 0),
        )

    def _procurement_board(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
    ) -> WorkbenchBoardRow:
        list_q = db.query(BomProcurementObjectList)
        loc_filter = location_in_clause(db, BomProcurementObjectList.location, location)
        if loc_filter is not None:
            list_q = list_q.filter(loc_filter)
        if vehicle_model:
            list_q = list_q.filter(BomProcurementObjectList.vehicle_model == vehicle_model)
        latest = list_q.order_by(BomProcurementObjectList.generated_at.desc()).first()
        if latest is None:
            return WorkbenchBoardRow(
                slice_id="procurement_object",
                label="采购对象清单",
                hash_page="bom-procurement-object-list",
                grain="list",
                row_count=0,
                pending_audit_count=0,
                incomplete_count=0,
                pending_confirm_count=0,
            )

        q = db.query(
            func.count(BomProcurementObject.id),
            func.coalesce(
                func.sum(case((BomProcurementObject.audit_status == "pending", 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((BomProcurementObject.section == "anomaly", 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((BomProcurementObject.confirm_status == "pending", 1), else_=0)),
                0,
            ),
        ).filter(BomProcurementObject.list_id == latest.id)
        total, pending_audit, anomaly, pending_confirm = q.one()
        return WorkbenchBoardRow(
            slice_id="procurement_object",
            label="采购对象清单",
            hash_page="bom-procurement-object-list",
            grain="list",
            row_count=int(total or 0),
            pending_audit_count=int(pending_audit or 0),
            incomplete_count=int(anomaly or 0),
            pending_confirm_count=int(pending_confirm or 0),
        )
