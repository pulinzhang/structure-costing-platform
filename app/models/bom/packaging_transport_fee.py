"""
BOM 包装运输费数据模型

审核锁定：
  audit_status == 'approved' 时，禁止修改、删除、导入覆盖；
  须先反审核为 pending。

唯一键：(location, year, vehicle_model, part_number)
核价只读 packaging_transport_total；其余列为对账明细。
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class BomPackagingTransportFee(AuditUserMixin, Base):
    """包装运输费表（按基地 + 年 + 项目 + 零件号）"""

    __tablename__ = "bom_packaging_transport_fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    location: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="采购基地，例：青岛、芜湖",
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="定价年度（如 2026）")

    vehicle_model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="项目/车型，例：T28",
    )

    part_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="零件号（取价匹配主键）",
    )

    part_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="产品名称",
    )

    packaging_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="包装类型，例：带轮料架、蓝色料盒",
    )

    pieces_per_pack: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="单包装数（件）",
    )

    fixture_length_mm: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="器具长(mm)"
    )
    fixture_width_mm: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="器具宽(mm)"
    )
    fixture_height_mm: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="器具高(mm)"
    )

    oem_stock_qty: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="上线及主机厂库存投入数量"
    )
    transit_qty: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="在途及返还周转投入数量"
    )
    company_stock_qty: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="公司库存周转投入数量"
    )
    total_fixture_qty: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="器具总投入数量"
    )

    fixture_unit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="器具单价(元)",
    )
    fixture_invest_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4),
        nullable=True,
        comment="器具投入总金额(元)",
    )

    unit_packaging_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="单件包装费(元/件)",
    )
    round_trip_transport_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="往返运输价格(元/车)",
    )
    unit_transport_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="单件运输费(元/件)",
    )
    fixture_maint_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="器具年损、维护费(元/件)",
    )
    other_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("0"),
        comment="其它费用合计(元/件)",
    )
    packaging_transport_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="包装运输费合计(元/件)，成品核价取价字段",
    )

    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 防扯皮溯源（对齐一事一议基价/加减价政策）
    excel_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="来源 Excel 文件名",
    )
    sheet_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="来源 Excel 工作表名",
    )
    excel_row: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="源数据在 Excel 中的行号（1-based）",
    )

    audit_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="审核状态：pending=待审，approved=已通过",
    )
    audited_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="最近一次审核人"
    )
    audited_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最近一次审核时间"
    )
    audit_remark: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="最近一次审核意见"
    )
    reverse_audited_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="反审核人"
    )
    reverse_audited_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="反审核时间"
    )
    reverse_audit_remark: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="反审核原因"
    )

    __table_args__ = (
        Index("ix_pkg_transport_location", "location"),
        Index("ix_pkg_transport_year", "year"),
        Index("ix_pkg_transport_vehicle_model", "vehicle_model"),
        Index("ix_pkg_transport_part_number", "part_number"),
        Index("ix_pkg_transport_audit_status", "audit_status"),
        Index(
            "ix_pkg_transport_scope",
            "location",
            "year",
            "vehicle_model",
        ),
        UniqueConstraint(
            "location",
            "year",
            "vehicle_model",
            "part_number",
            name="uix_pkg_transport_location_year_vehicle_part",
        ),
        ForeignKeyConstraint(
            ["location", "vehicle_model"],
            ["vehicle_models.location", "vehicle_models.vehicle_model"],
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            name="fk_bom_packaging_transport_fees_vehicle_models",
        ),
    )
