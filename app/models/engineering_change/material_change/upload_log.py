"""材料变更上传头 — engineering_change_material_upload_logs。"""

from sqlalchemy import ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class EngineeringChangeMaterialUploadLog(AuditUserMixin, Base):
    """一次材料变更上传（含失败）。成功 UNIQUE 含厂。"""

    __tablename__ = "engineering_change_material_upload_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    task_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="异步任务 ID"
    )
    upload_file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("upload_files.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="存档 Excel",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending / success / failed",
    )
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目")
    stamping_supplier: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey("suppliers.full_name", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=True,
        comment="冲压工厂；入队时可空，解析成功后写入",
    )
    change_version: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="MAT-YYYYMM"
    )
    effective_year: Mapped[int] = mapped_column(Integer, nullable=False, comment="生效年")
    effective_month: Mapped[int] = mapped_column(Integer, nullable=False, comment="生效月 1–12")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="源文件名")
    message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因或说明")
    part_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="切点行数")

    __table_args__ = (
        Index(
            "uq_ecm_upload_success_version",
            "location",
            "vehicle_model",
            "stamping_supplier",
            "change_version",
            unique=True,
            sqlite_where=text("status = 'success'"),
        ),
    )
