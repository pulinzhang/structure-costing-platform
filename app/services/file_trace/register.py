"""文件溯源登记（供 upload Service 调用）。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.models.file_trace.upload_file import UploadFile
from app.repositories.file_trace.upload_file_repository import (
    UploadFileInsert,
    UploadFileRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.categories import VALID_FILE_CATEGORIES
from app.services.file_trace.path_utils import resolve_upload_path, to_upload_relpath

_repo = UploadFileRepository()


def register_existing(
    db: Session,
    *,
    file_category: str,
    stored_relpath: str,
    original_filename: str,
    current_user: UserVO,
    file_hash: str | None = None,
    location: str | None = None,
    year: int | None = None,
    month: int | None = None,
    vehicle_model: str | None = None,
    bom_version: str | None = None,
    process_version: str | None = None,
    stamping_supplier: str | None = None,
    business_ref_type: str | None = None,
    business_ref_id: int | None = None,
    supersede_same_scope: bool = True,
) -> UploadFile:
    """登记已落盘原件。须与上游业务同一事务、commit 前调用。"""
    if file_category not in VALID_FILE_CATEGORIES:
        raise ValueError(f"不支持的文件分类: {file_category}")

    relpath = (
        to_upload_relpath(stored_relpath)
        if Path(stored_relpath).is_absolute()
        else stored_relpath.replace("\\", "/")
    )
    absolute_path = resolve_upload_path(relpath)
    if not absolute_path.is_file():
        raise ValueError(f"原件不存在: {relpath}")

    computed_hash = file_hash
    if not computed_hash:
        digest = hashlib.sha256()
        with open(absolute_path, "rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(chunk)
        computed_hash = digest.hexdigest()

    file_size = absolute_path.stat().st_size
    extension = Path(original_filename).suffix.lower() or Path(absolute_path.name).suffix.lower()
    audit = audit_create(current_user)

    if supersede_same_scope:
        active_rows = _repo.list_active_by_scope(
            db,
            file_category=file_category,
            location=location,
            year=year,
            month=month,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            process_version=process_version,
            stamping_supplier=stamping_supplier or None,
        )
    else:
        active_rows = []

    row = _repo.create(
        db,
        UploadFileInsert(
            file_category=file_category,
            original_filename=Path(original_filename).name,
            stored_relpath=relpath,
            file_hash=computed_hash,
            file_size=file_size,
            extension=extension,
            location=location,
            year=year,
            month=month,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            process_version=process_version,
            stamping_supplier=stamping_supplier or None,
            business_ref_type=business_ref_type,
            business_ref_id=business_ref_id,
            status="active",
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
        ),
    )

    if active_rows:
        _repo.mark_superseded(
            db,
            active_rows,
            superseded_by_id=row.id,
            updated_by=audit["updated_by"],
        )

    return row
