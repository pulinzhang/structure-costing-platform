"""engineering_change_orders 数据访问。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.engineering_change.design_change.change_order import EngineeringChangeOrder
from app.models.engineering_change.design_change.upload_log import EngineeringChangeUploadLog
from app.repositories.persist import model_from_payload


@dataclass(slots=True)
class EngineeringChangeOrderInsert:
    upload_log_id: int
    upload_file_id: int
    before_assembly_node_id: int
    excel_row: int
    project_code: str
    effective_period_text: str
    change_type: str
    before_assembly_part_number: str
    after_assembly_part_number: str | None
    assembly_name: str | None
    part_level: str
    before_part_number: str | None
    after_part_number: str | None
    part_name: str | None
    created_by: str | None
    updated_by: str | None
    seq_no: int | None = None
    status: str = "active"


@dataclass(slots=True)
class EngineeringChangeOrderListRow:
    """列表一行 = 变更单（失败/进行中无变更单时 change_order 为空）。"""

    log: EngineeringChangeUploadLog
    change_order: EngineeringChangeOrder | None


class EngineeringChangeOrderRepository:
    """变更单表 CRUD / 查询。"""

    def get_by_id(self, db: Session, change_order_id: int) -> EngineeringChangeOrder | None:
        return (
            db.query(EngineeringChangeOrder)
            .filter(EngineeringChangeOrder.id == change_order_id)
            .first()
        )

    def list_by_upload_log_id(
        self, db: Session, upload_log_id: int
    ) -> list[EngineeringChangeOrder]:
        return (
            db.query(EngineeringChangeOrder)
            .filter(EngineeringChangeOrder.upload_log_id == upload_log_id)
            .order_by(EngineeringChangeOrder.excel_row.asc(), EngineeringChangeOrder.id.asc())
            .all()
        )

    def list_page(
        self,
        db: Session,
        *,
        skip: int,
        limit: int,
        location: str | None = None,
        vehicle_model: str | None = None,
        effective_year: int | None = None,
        effective_month: int | None = None,
        status: str | None = None,
        change_type: str | None = None,
    ) -> tuple[list[EngineeringChangeOrderListRow], int]:
        query = db.query(EngineeringChangeUploadLog, EngineeringChangeOrder).outerjoin(
            EngineeringChangeOrder,
            EngineeringChangeOrder.upload_log_id == EngineeringChangeUploadLog.id,
        )
        if location:
            query = query.filter(EngineeringChangeUploadLog.location == location)
        if vehicle_model:
            query = query.filter(EngineeringChangeUploadLog.vehicle_model == vehicle_model)
        if effective_year is not None:
            query = query.filter(EngineeringChangeUploadLog.effective_year == effective_year)
        if effective_month is not None:
            query = query.filter(EngineeringChangeUploadLog.effective_month == effective_month)
        if status:
            query = query.filter(EngineeringChangeUploadLog.status == status)
        if change_type:
            query = query.filter(EngineeringChangeOrder.change_type == change_type)
        total = query.count()
        rows = (
            query.order_by(
                EngineeringChangeUploadLog.id.desc(),
                EngineeringChangeOrder.excel_row.asc(),
                EngineeringChangeOrder.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [
            EngineeringChangeOrderListRow(log=log_row, change_order=change_order)
            for log_row, change_order in rows
        ], total

    def create(self, db: Session, payload: EngineeringChangeOrderInsert) -> EngineeringChangeOrder:
        row = model_from_payload(EngineeringChangeOrder, payload)
        db.add(row)
        db.flush()
        return row

    def delete_by_upload_log_id(self, db: Session, upload_log_id: int) -> int:
        deleted = (
            db.query(EngineeringChangeOrder)
            .filter(EngineeringChangeOrder.upload_log_id == upload_log_id)
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(deleted)

    def list_later_success_using_after_as_before(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        after_assembly_part_number: str,
        after_upload_log_id: int,
    ) -> list[EngineeringChangeOrder]:
        """其后以本本 after_assembly 为变更前总成、仍 active 的成功变更。"""
        return (
            db.query(EngineeringChangeOrder)
            .join(
                EngineeringChangeUploadLog,
                EngineeringChangeUploadLog.id == EngineeringChangeOrder.upload_log_id,
            )
            .filter(
                EngineeringChangeUploadLog.location == location,
                EngineeringChangeUploadLog.vehicle_model == vehicle_model,
                EngineeringChangeUploadLog.status == "success",
                EngineeringChangeOrder.status == "active",
                EngineeringChangeOrder.before_assembly_part_number == after_assembly_part_number,
                EngineeringChangeUploadLog.id > after_upload_log_id,
            )
            .all()
        )
