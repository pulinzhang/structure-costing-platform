"""engineering_change_material_orders 数据访问。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.engineering_change.material_change.order import EngineeringChangeMaterialOrder
from app.models.engineering_change.material_change.upload_log import (
    EngineeringChangeMaterialUploadLog,
)
from app.repositories.persist import model_from_payload


@dataclass(slots=True)
class MaterialChangeOrderListRow:
    """列表一行 = 变更单行。失败或进行中没有切点时 order 为空。"""

    log: EngineeringChangeMaterialUploadLog
    order: EngineeringChangeMaterialOrder | None


@dataclass(slots=True)
class MaterialChangeOrderInsert:
    upload_log_id: int
    upload_file_id: int
    change_version: str
    excel_row: int | None
    location: str
    stamping_supplier: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    part_number: str
    before_material: str
    after_material: str
    before_thickness: Decimal
    after_thickness: Decimal
    interchangeability: str
    part_name: str
    source_part_id: int
    created_by: str | None
    updated_by: str | None


class MaterialChangeOrderRepository:
    def list_page(
        self,
        db: Session,
        *,
        skip: int,
        limit: int,
        location: str | None = None,
        vehicle_model: str | None = None,
        change_version: str | None = None,
        effective_year: int | None = None,
        effective_month: int | None = None,
        status: str | None = None,
    ) -> tuple[list[MaterialChangeOrderListRow], int]:
        """一本成功 Excel 出 N 行切点。无切点的头仍出一行。"""
        query = db.query(
            EngineeringChangeMaterialUploadLog, EngineeringChangeMaterialOrder
        ).outerjoin(
            EngineeringChangeMaterialOrder,
            EngineeringChangeMaterialOrder.upload_log_id == EngineeringChangeMaterialUploadLog.id,
        )
        if location:
            query = query.filter(EngineeringChangeMaterialUploadLog.location == location)
        if vehicle_model:
            query = query.filter(EngineeringChangeMaterialUploadLog.vehicle_model == vehicle_model)
        if change_version:
            query = query.filter(
                EngineeringChangeMaterialUploadLog.change_version == change_version
            )
        if effective_year is not None:
            query = query.filter(
                EngineeringChangeMaterialUploadLog.effective_year == effective_year
            )
        if effective_month is not None:
            query = query.filter(
                EngineeringChangeMaterialUploadLog.effective_month == effective_month
            )
        if status:
            query = query.filter(EngineeringChangeMaterialUploadLog.status == status)
        total = query.count()
        rows = (
            query.order_by(
                EngineeringChangeMaterialUploadLog.id.desc(),
                EngineeringChangeMaterialOrder.excel_row.asc(),
                EngineeringChangeMaterialOrder.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [
            MaterialChangeOrderListRow(log=log_row, order=order) for log_row, order in rows
        ], total

    def create(
        self, db: Session, payload: MaterialChangeOrderInsert
    ) -> EngineeringChangeMaterialOrder:
        row = model_from_payload(EngineeringChangeMaterialOrder, payload)
        db.add(row)
        db.flush()
        return row

    def list_by_upload_log_id(
        self, db: Session, upload_log_id: int
    ) -> list[EngineeringChangeMaterialOrder]:
        return (
            db.query(EngineeringChangeMaterialOrder)
            .filter(EngineeringChangeMaterialOrder.upload_log_id == upload_log_id)
            .order_by(EngineeringChangeMaterialOrder.excel_row.asc())
            .all()
        )

    def delete(self, db: Session, row: EngineeringChangeMaterialOrder) -> None:
        db.delete(row)
        db.flush()
