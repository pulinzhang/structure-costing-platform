"""engineering_change_material_upload_logs 数据访问。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.engineering_change.material_change.upload_log import (
    EngineeringChangeMaterialUploadLog,
)
from app.repositories.persist import model_from_payload


@dataclass(slots=True)
class MaterialChangeUploadLogInsert:
    upload_file_id: int
    location: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    original_filename: str
    created_by: str | None
    updated_by: str | None
    task_id: str | None = None
    status: str = "pending"
    message: str | None = None
    stamping_supplier: str | None = None
    change_version: str | None = None
    part_count: int = 0


@dataclass(slots=True)
class MaterialChangeUploadLogUpdate:
    status: str | None = None
    message: str | None = None
    task_id: str | None = None
    stamping_supplier: str | None = None
    change_version: str | None = None
    part_count: int | None = None
    updated_by: str | None = None


class MaterialChangeUploadLogRepository:
    def get_by_id(self, db: Session, log_id: int) -> EngineeringChangeMaterialUploadLog | None:
        return (
            db.query(EngineeringChangeMaterialUploadLog)
            .filter(EngineeringChangeMaterialUploadLog.id == log_id)
            .first()
        )

    def create(
        self, db: Session, payload: MaterialChangeUploadLogInsert
    ) -> EngineeringChangeMaterialUploadLog:
        row = model_from_payload(EngineeringChangeMaterialUploadLog, payload)
        db.add(row)
        db.flush()
        return row

    def update(
        self,
        db: Session,
        row: EngineeringChangeMaterialUploadLog,
        payload: MaterialChangeUploadLogUpdate,
    ) -> EngineeringChangeMaterialUploadLog:
        for field_name, value in (
            ("status", payload.status),
            ("message", payload.message),
            ("task_id", payload.task_id),
            ("stamping_supplier", payload.stamping_supplier),
            ("change_version", payload.change_version),
            ("part_count", payload.part_count),
            ("updated_by", payload.updated_by),
        ):
            if value is not None:
                setattr(row, field_name, value)
        db.flush()
        return row

    def delete(self, db: Session, row: EngineeringChangeMaterialUploadLog) -> None:
        db.delete(row)
        db.flush()

    def get_success_version(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        stamping_supplier: str,
        change_version: str,
    ) -> EngineeringChangeMaterialUploadLog | None:
        return (
            db.query(EngineeringChangeMaterialUploadLog)
            .filter(
                EngineeringChangeMaterialUploadLog.status == "success",
                EngineeringChangeMaterialUploadLog.location == location,
                EngineeringChangeMaterialUploadLog.vehicle_model == vehicle_model,
                EngineeringChangeMaterialUploadLog.stamping_supplier == stamping_supplier,
                EngineeringChangeMaterialUploadLog.change_version == change_version,
            )
            .first()
        )

    def get_pending(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        effective_year: int,
        effective_month: int,
        exclude_id: int | None = None,
    ) -> EngineeringChangeMaterialUploadLog | None:
        query = db.query(EngineeringChangeMaterialUploadLog).filter(
            EngineeringChangeMaterialUploadLog.status == "pending",
            EngineeringChangeMaterialUploadLog.location == location,
            EngineeringChangeMaterialUploadLog.vehicle_model == vehicle_model,
            EngineeringChangeMaterialUploadLog.effective_year == effective_year,
            EngineeringChangeMaterialUploadLog.effective_month == effective_month,
        )
        if exclude_id is not None:
            query = query.filter(EngineeringChangeMaterialUploadLog.id != exclude_id)
        return query.first()
