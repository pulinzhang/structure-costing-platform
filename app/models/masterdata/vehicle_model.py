"""项目主数据：挂在已登记基地上，复合主键 (location, vehicle_model)。"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class VehicleModel(AuditUserMixin, Base):
    """项目。禁止 relationship 指向冲压 / BOM；基地 Model 禁止指向本表。"""

    __tablename__ = "vehicle_models"

    location: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("locations.location", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
        comment="所属基地规范名，创建后只读",
    )
    vehicle_model: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="项目代号，规范化大写，创建后只读",
    )
    effective_year: Mapped[int] = mapped_column(Integer, nullable=False, comment="生效年")
    effective_month: Mapped[int] = mapped_column(Integer, nullable=False, comment="生效月 1–12")
    expiry_year: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="失效年，与失效月同空或同有"
    )
    expiry_month: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="失效月 1–12")
