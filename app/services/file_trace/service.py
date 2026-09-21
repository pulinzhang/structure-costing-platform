"""文件溯源读服务：列表、详情、鉴权下载。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.file_trace.upload_file_repository import UploadFileRepository
from app.schemas.dto.file_trace_dto import UploadFileListQuery
from app.schemas.vo.file_trace_vo import UploadFileFiltersVO, UploadFileVO
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.categories import category_label, resolve_allowed_categories
from app.services.file_trace.path_utils import resolve_upload_path
from app.services.masterdata.vehicle_model.service import VehicleModelService

_repo = UploadFileRepository()


class UploadFileService:
    """溯源列表 / 下载。"""

    def list_files(
        self,
        db: Session,
        query: UploadFileListQuery,
        current_user: UserVO,
    ) -> tuple[list[UploadFileVO], int]:
        allowed = resolve_allowed_categories(current_user)
        if query.file_category and query.file_category not in allowed:
            return [], 0

        rows, total = _repo.paginate(
            db,
            query,
            allowed,
            skip=(query.page - 1) * query.size,
            limit=query.size,
        )
        return [UploadFileVO.model_validate(row) for row in rows], total

    def get_filters(
        self,
        db: Session,
        current_user: UserVO,
    ) -> UploadFileFiltersVO:
        allowed = resolve_allowed_categories(current_user)
        values = _repo.collect_filter_values(db, allowed)
        labels = {code: category_label(code) for code in allowed}
        return UploadFileFiltersVO(
            allowed_categories=allowed,
            category_labels=labels,
            locations=[str(v) for v in values["locations"]],
            years=[int(v) for v in values["years"]],
            months=[int(v) for v in values["months"]],
            vehicle_models=VehicleModelService().list_filter_codes(db),
            creators=[str(v) for v in values["creators"]],
        )

    def get_file(
        self,
        db: Session,
        file_id: int,
        current_user: UserVO,
    ) -> UploadFileVO:
        row = _repo.get_by_id(db, file_id)
        if not row:
            raise NotFoundException(f"文件不存在: id={file_id}")
        allowed = resolve_allowed_categories(current_user)
        if row.file_category not in allowed:
            raise NotFoundException(f"文件不存在: id={file_id}")
        return UploadFileVO.model_validate(row)

    def resolve_download(
        self,
        db: Session,
        file_id: int,
        current_user: UserVO,
    ) -> tuple[Path, str, str]:
        row = _repo.get_by_id(db, file_id)
        if not row:
            raise NotFoundException(f"文件不存在: id={file_id}")

        allowed = resolve_allowed_categories(current_user)
        if row.file_category not in allowed:
            raise NotFoundException(f"文件不存在: id={file_id}")

        if row.status not in {"active", "superseded"}:
            raise BusinessException("该文件不可下载")

        try:
            absolute_path = resolve_upload_path(row.stored_relpath)
        except ValueError as exc:
            raise BusinessException(str(exc)) from exc

        if not absolute_path.is_file():
            raise NotFoundException("原件已丢失，请联系管理员")

        media_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if row.extension == ".xlsx"
            else "application/vnd.ms-excel"
        )
        return absolute_path, row.original_filename, media_type
