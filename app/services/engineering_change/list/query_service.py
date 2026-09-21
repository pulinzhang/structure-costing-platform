"""工程变更单列表查询。当时 Excel 下载走文件溯源。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.exceptions.base import NotFoundException
from app.repositories.engineering_change.change_order_repository import (
    EngineeringChangeOrderListRow,
    EngineeringChangeOrderRepository,
)
from app.repositories.engineering_change.upload_log_repository import (
    EngineeringChangeUploadLogRepository,
)
from app.schemas.dto.engineering_change_dto import EngineeringChangeOrderQueryDTO
from app.schemas.vo.engineering_change_vo import EngineeringChangeListRowVO
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.service import UploadFileService


class EngineeringChangeQueryService:
    def __init__(self) -> None:
        self.log_repo = EngineeringChangeUploadLogRepository()
        self.change_order_repo = EngineeringChangeOrderRepository()

    def paginate(
        self, db: Session, query: EngineeringChangeOrderQueryDTO
    ) -> tuple[list[EngineeringChangeListRowVO], int]:
        skip = (query.page - 1) * query.size
        rows, total = self.change_order_repo.list_page(
            db,
            skip=skip,
            limit=query.size,
            location=query.location,
            vehicle_model=query.vehicle_model,
            effective_year=query.effective_year,
            effective_month=query.effective_month,
            status=query.status,
            change_type=query.change_type,
        )
        return [self._to_list_row(row) for row in rows], total

    def resolve_original_file(
        self, db: Session, upload_log_id: int, current_user: UserVO
    ) -> tuple[Path, str, str]:
        log_row = self.log_repo.get_by_id(db, upload_log_id)
        if log_row is None:
            raise NotFoundException("工程变更记录不存在")
        return UploadFileService().resolve_download(db, log_row.upload_file_id, current_user)

    def _to_list_row(self, row: EngineeringChangeOrderListRow) -> EngineeringChangeListRowVO:
        log_row = row.log
        change_order = row.change_order
        if change_order is None:
            return EngineeringChangeListRowVO(
                upload_log_id=log_row.id,
                location=log_row.location,
                vehicle_model=log_row.vehicle_model,
                effective_year=log_row.effective_year,
                effective_month=log_row.effective_month,
                status=log_row.status,
                original_filename=log_row.original_filename,
                task_id=log_row.task_id,
                message=log_row.message,
                created_by=log_row.created_by,
                created_at=log_row.created_at,
            )
        return EngineeringChangeListRowVO(
            change_order_id=change_order.id,
            upload_log_id=log_row.id,
            excel_row=change_order.excel_row,
            project_code=change_order.project_code,
            effective_period_text=change_order.effective_period_text,
            change_type=change_order.change_type,
            before_assembly_part_number=change_order.before_assembly_part_number,
            after_assembly_part_number=change_order.after_assembly_part_number,
            assembly_name=change_order.assembly_name,
            part_level=change_order.part_level,
            before_part_number=change_order.before_part_number,
            after_part_number=change_order.after_part_number,
            part_name=change_order.part_name,
            seq_no=change_order.seq_no,
            location=log_row.location,
            vehicle_model=log_row.vehicle_model,
            effective_year=log_row.effective_year,
            effective_month=log_row.effective_month,
            status=log_row.status,
            original_filename=log_row.original_filename,
            task_id=log_row.task_id,
            message=log_row.message,
            created_by=log_row.created_by,
            created_at=log_row.created_at,
        )
