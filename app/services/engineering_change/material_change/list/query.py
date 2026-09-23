"""材料变更列表与原件。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.exceptions.base import NotFoundException
from app.repositories.engineering_change.material_change.order_repository import (
    MaterialChangeOrderListRow,
    MaterialChangeOrderRepository,
)
from app.repositories.engineering_change.material_change.upload_log_repository import (
    MaterialChangeUploadLogRepository,
)
from app.schemas.dto.engineering_change.material_change import MaterialChangeUploadQueryDTO
from app.schemas.vo.engineering_change.material_change import MaterialChangeUploadListRowVO
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.service import UploadFileService

_log_repo = MaterialChangeUploadLogRepository()
_order_repo = MaterialChangeOrderRepository()


class MaterialChangeQueryService:
    def paginate(
        self, db: Session, query: MaterialChangeUploadQueryDTO
    ) -> tuple[list[MaterialChangeUploadListRowVO], int]:
        rows, total = _order_repo.list_page(
            db,
            skip=(query.page - 1) * query.size,
            limit=query.size,
            location=query.location,
            vehicle_model=query.vehicle_model,
            change_version=query.change_version,
            effective_year=query.effective_year,
            effective_month=query.effective_month,
            status=query.status,
        )
        return [_to_list_row(row) for row in rows], total

    def resolve_original_file(
        self, db: Session, upload_log_id: int, current_user: UserVO
    ) -> tuple[Path, str, str]:
        log_row = _log_repo.get_by_id(db, upload_log_id)
        if log_row is None:
            raise NotFoundException("材料变更记录不存在")
        return UploadFileService().resolve_download(db, log_row.upload_file_id, current_user)


def _to_list_row(row: MaterialChangeOrderListRow) -> MaterialChangeUploadListRowVO:
    log_row = row.log
    order = row.order
    if order is None:
        return MaterialChangeUploadListRowVO(
            upload_log_id=log_row.id,
            location=log_row.location,
            vehicle_model=log_row.vehicle_model,
            stamping_supplier=log_row.stamping_supplier,
            change_version=log_row.change_version,
            effective_year=log_row.effective_year,
            effective_month=log_row.effective_month,
            status=log_row.status,
            original_filename=log_row.original_filename,
            message=log_row.message,
            created_by=log_row.created_by,
            created_at=log_row.created_at,
        )
    return MaterialChangeUploadListRowVO(
        order_id=order.id,
        upload_log_id=log_row.id,
        excel_row=order.excel_row,
        location=order.location,
        vehicle_model=order.vehicle_model,
        stamping_supplier=order.stamping_supplier,
        change_version=order.change_version,
        effective_year=order.effective_year,
        effective_month=order.effective_month,
        part_number=order.part_number,
        part_name=order.part_name,
        before_material=order.before_material,
        after_material=order.after_material,
        before_thickness=order.before_thickness,
        after_thickness=order.after_thickness,
        interchangeability=order.interchangeability,
        status=log_row.status,
        original_filename=log_row.original_filename,
        message=log_row.message,
        created_by=log_row.created_by,
        created_at=log_row.created_at,
    )
