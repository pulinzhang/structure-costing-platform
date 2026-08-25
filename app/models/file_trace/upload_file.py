"""已落盘业务 Excel 登记中心。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class UploadFile(Base, AuditUserMixin):
    """upload_files — 溯源列表单一真相。"""

    __tablename__ = "upload_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_category: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True, comment="业务分类"
    )
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="用户上传时的文件名"
    )
    stored_relpath: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True, comment="相对 UPLOAD_DIR 路径"
    )
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="SHA256 hex")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="字节大小")
    extension: Mapped[str] = mapped_column(String(20), nullable=False, comment="小写扩展名")
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vehicle_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bom_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    process_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stamping_supplier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    business_ref_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    business_ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="active/superseded/missing",
    )
    superseded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("upload_files.id"), nullable=True
    )

    superseded_by: Mapped[UploadFile | None] = relationship(
        "UploadFile",
        remote_side="UploadFile.id",
        foreign_keys=[superseded_by_id],
    )

    __table_args__ = (
        Index("ix_upload_files_category_created", "file_category", "created_at"),
        Index("ix_upload_files_location_year_month", "location", "year", "month"),
        Index("ix_upload_files_vehicle_bom_version", "vehicle_model", "bom_version"),
        Index(
            "ix_upload_files_vehicle_process_version",
            "vehicle_model",
            "process_version",
        ),
    )
