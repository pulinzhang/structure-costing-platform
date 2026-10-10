"""engineering_change_upload_logs 数据访问。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.engineering_change.design_change.upload_log import EngineeringChangeUploadLog
from app.repositories.persist import model_from_payload


@dataclass(slots=True)
class EngineeringChangeUploadLogInsert:
    upload_file_id: int
    location: str
    vehicle_model: str
    customer_name: str
    effective_year: int
    effective_month: int
    original_filename: str
    created_by: str | None
    updated_by: str | None
    task_id: str | None = None
    status: str = "pending"
    message: str | None = None


@dataclass(slots=True)
class EngineeringChangeUploadLogUpdate:
    status: str | None = None
    message: str | None = None
    task_id: str | None = None
    process_inserted_count: int | None = None
    die_inserted_count: int | None = None
    procurement_object_inserted_count: int | None = None
    welding_breakdown_inserted_count: int | None = None
    not_install_count: int | None = None
    has_bom_assembly: bool | None = None
    customer_name: str | None = None
    updated_by: str | None = None


class EngineeringChangeUploadLogRepository:
    """上传头 CRUD / 查询。"""

    def get_by_id(self, db: Session, log_id: int) -> EngineeringChangeUploadLog | None:
        return (
            db.query(EngineeringChangeUploadLog)
            .filter(EngineeringChangeUploadLog.id == log_id)
            .first()
        )

    def get_by_task_id(self, db: Session, task_id: str) -> EngineeringChangeUploadLog | None:
        return (
            db.query(EngineeringChangeUploadLog)
            .filter(EngineeringChangeUploadLog.task_id == task_id)
            .first()
        )

    def create(
        self, db: Session, payload: EngineeringChangeUploadLogInsert
    ) -> EngineeringChangeUploadLog:
        row = model_from_payload(EngineeringChangeUploadLog, payload)
        db.add(row)
        db.flush()
        return row

    def update(
        self,
        db: Session,
        row: EngineeringChangeUploadLog,
        payload: EngineeringChangeUploadLogUpdate,
    ) -> EngineeringChangeUploadLog:
        for field_name, value in (
            ("status", payload.status),
            ("message", payload.message),
            ("task_id", payload.task_id),
            ("process_inserted_count", payload.process_inserted_count),
            ("die_inserted_count", payload.die_inserted_count),
            ("procurement_object_inserted_count", payload.procurement_object_inserted_count),
            ("welding_breakdown_inserted_count", payload.welding_breakdown_inserted_count),
            ("not_install_count", payload.not_install_count),
            ("has_bom_assembly", payload.has_bom_assembly),
            ("customer_name", payload.customer_name),
            ("updated_by", payload.updated_by),
        ):
            if value is not None:
                setattr(row, field_name, value)
        db.flush()
        return row

    def delete(self, db: Session, row: EngineeringChangeUploadLog) -> None:
        db.delete(row)
        db.flush()

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
    ) -> tuple[list[EngineeringChangeUploadLog], int]:
        query = db.query(EngineeringChangeUploadLog)
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
        total = query.count()
        rows = query.order_by(EngineeringChangeUploadLog.id.desc()).offset(skip).limit(limit).all()
        return rows, total

    def list_busy_after_assembly(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        after_assembly_part_number: str,
    ) -> list[EngineeringChangeUploadLog]:
        """同范围下占用该变更后总成的 pending/success（未回滚）头。"""
        from app.models.engineering_change.design_change.change_order import EngineeringChangeOrder

        return (
            db.query(EngineeringChangeUploadLog)
            .join(
                EngineeringChangeOrder,
                EngineeringChangeOrder.upload_log_id == EngineeringChangeUploadLog.id,
            )
            .filter(
                EngineeringChangeUploadLog.location == location,
                EngineeringChangeUploadLog.vehicle_model == vehicle_model,
                EngineeringChangeUploadLog.status.in_(("pending", "success")),
                EngineeringChangeOrder.after_assembly_part_number == after_assembly_part_number,
                EngineeringChangeOrder.status == "active",
            )
            .all()
        )
