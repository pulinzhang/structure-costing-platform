"""upload_files 数据访问。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from app.models.file_trace.upload_file import UploadFile
from app.schemas.dto.file_trace_dto import UploadFileListQuery


@dataclass(slots=True)
class UploadFileInsert:
    file_category: str
    original_filename: str
    stored_relpath: str
    file_hash: str
    file_size: int
    extension: str
    location: str | None
    year: int | None
    month: int | None
    vehicle_model: str | None
    bom_version: str | None
    process_version: str | None
    stamping_supplier: str | None
    business_ref_type: str | None
    business_ref_id: int | None
    status: str
    created_by: str | None
    updated_by: str | None


class UploadFileRepository:
    """upload_files CRUD / 查询。"""

    def get_by_relpath(self, db: Session, stored_relpath: str) -> UploadFile | None:
        return db.query(UploadFile).filter(UploadFile.stored_relpath == stored_relpath).first()

    def get_by_id(self, db: Session, file_id: int) -> UploadFile | None:
        return db.query(UploadFile).filter(UploadFile.id == file_id).first()

    def create(self, db: Session, payload: UploadFileInsert) -> UploadFile:
        row = UploadFile(
            file_category=payload.file_category,
            original_filename=payload.original_filename,
            stored_relpath=payload.stored_relpath,
            file_hash=payload.file_hash,
            file_size=payload.file_size,
            extension=payload.extension,
            location=payload.location,
            year=payload.year,
            month=payload.month,
            vehicle_model=payload.vehicle_model,
            bom_version=payload.bom_version,
            process_version=payload.process_version,
            stamping_supplier=payload.stamping_supplier,
            business_ref_type=payload.business_ref_type,
            business_ref_id=payload.business_ref_id,
            status=payload.status,
            created_by=payload.created_by,
            updated_by=payload.updated_by,
        )
        db.add(row)
        db.flush()
        return row

    def list_active_by_scope(
        self,
        db: Session,
        *,
        file_category: str,
        location: str | None = None,
        year: int | None = None,
        month: int | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        process_version: str | None = None,
        stamping_supplier: str | None = None,
    ) -> list[UploadFile]:
        query = db.query(UploadFile).filter(
            UploadFile.file_category == file_category,
            UploadFile.status == "active",
        )
        query = self._apply_scope_filters(
            query,
            file_category=file_category,
            location=location,
            year=year,
            month=month,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            process_version=process_version,
            stamping_supplier=stamping_supplier,
        )
        return query.all()

    def mark_superseded(
        self,
        db: Session,
        rows: list[UploadFile],
        *,
        superseded_by_id: int,
        updated_by: str | None,
    ) -> None:
        for row in rows:
            row.status = "superseded"
            row.superseded_by_id = superseded_by_id
            row.updated_by = updated_by

    def paginate(
        self,
        db: Session,
        query: UploadFileListQuery,
        allowed_categories: list[str],
        *,
        skip: int,
        limit: int,
    ) -> tuple[list[UploadFile], int]:
        if not allowed_categories:
            return [], 0

        q = db.query(UploadFile).filter(UploadFile.file_category.in_(allowed_categories))

        if query.file_category:
            q = q.filter(UploadFile.file_category == query.file_category)

        status = query.status or "active"
        q = q.filter(UploadFile.status == status)

        if query.location:
            q = q.filter(UploadFile.location == query.location)
        if query.year is not None:
            q = q.filter(UploadFile.year == query.year)
        if query.month is not None:
            q = q.filter(UploadFile.month == query.month)
        if query.vehicle_model:
            q = q.filter(UploadFile.vehicle_model.like(f"%{query.vehicle_model}%"))
        if query.filename:
            q = q.filter(UploadFile.original_filename.like(f"%{query.filename}%"))
        if query.created_by:
            q = q.filter(UploadFile.created_by == query.created_by)
        if query.uploaded_from:
            start = datetime.combine(query.uploaded_from, time.min)
            q = q.filter(UploadFile.created_at >= start)
        if query.uploaded_to:
            end = datetime.combine(query.uploaded_to, time.max)
            q = q.filter(UploadFile.created_at <= end)

        total = q.count()
        rows = (
            q.order_by(UploadFile.created_at.desc(), UploadFile.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def collect_filter_values(
        self,
        db: Session,
        allowed_categories: list[str],
    ) -> dict[str, list[str | int]]:
        if not allowed_categories:
            return {
                "categories": [],
                "locations": [],
                "years": [],
                "months": [],
                "vehicle_models": [],
                "creators": [],
            }

        base = db.query(UploadFile).filter(
            UploadFile.file_category.in_(allowed_categories),
            UploadFile.status == "active",
        )

        categories = sorted(
            {row[0] for row in base.with_entities(UploadFile.file_category).distinct()}
        )
        locations = sorted(
            {row[0] for row in base.with_entities(UploadFile.location).distinct() if row[0]}
        )
        years = sorted(
            {
                row[0]
                for row in base.with_entities(UploadFile.year).distinct()
                if row[0] is not None
            },
            reverse=True,
        )
        months = sorted(
            {
                row[0]
                for row in base.with_entities(UploadFile.month).distinct()
                if row[0] is not None
            }
        )
        vehicle_models = sorted(
            {row[0] for row in base.with_entities(UploadFile.vehicle_model).distinct() if row[0]}
        )
        creators = sorted(
            {row[0] for row in base.with_entities(UploadFile.created_by).distinct() if row[0]}
        )

        return {
            "categories": categories,
            "locations": locations,
            "years": years,
            "months": months,
            "vehicle_models": vehicle_models,
            "creators": creators,
        }

    @staticmethod
    def _apply_scope_filters(
        query: Query[UploadFile],
        *,
        file_category: str,
        location: str | None,
        year: int | None,
        month: int | None,
        vehicle_model: str | None,
        bom_version: str | None,
        process_version: str | None,
        stamping_supplier: str | None,
    ) -> Query[UploadFile]:
        if file_category == "bom_material":
            return query.filter(
                UploadFile.location == location,
                UploadFile.vehicle_model == vehicle_model,
                UploadFile.bom_version == bom_version,
            )
        if file_category == "stamping_process":
            filters = [
                UploadFile.location == location,
                UploadFile.vehicle_model == vehicle_model,
                UploadFile.process_version == process_version,
            ]
            if stamping_supplier:
                filters.append(UploadFile.stamping_supplier == stamping_supplier)
            else:
                filters.append(
                    or_(
                        UploadFile.stamping_supplier.is_(None),
                        UploadFile.stamping_supplier == "",
                    )
                )
            return query.filter(and_(*filters))
        if file_category in {"steel_base_price", "steel_price_policy"}:
            return query.filter(
                UploadFile.year == year,
                UploadFile.month == month,
            )
        if file_category == "bom_packaging_transport_fee":
            return query.filter(
                UploadFile.year == year,
                UploadFile.location == location,
                UploadFile.vehicle_model == vehicle_model,
            )
        if file_category == "stamping_tonnage_price":
            return query.filter(
                UploadFile.year == year,
                UploadFile.location == location,
            )
        if file_category == "bom_welding_unit_price":
            return query.filter(
                UploadFile.year == year,
                UploadFile.location == location,
            )
        if file_category == "bom_annual_part_price":
            return query.filter(
                UploadFile.year == year,
                UploadFile.location == location,
            )
        return query
