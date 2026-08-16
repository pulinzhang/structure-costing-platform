"""
BOM 焊接工艺拆解数据模型

主表：有焊接信息的 BOM 节点（含装配用量 assembly_qty）
明细：单件焊接过程量（process_qty），一种工艺一行

审核锁定在主表：
  audit_status == 'approved' 时禁止修改、删除、重新生成覆盖；
  须先反审核为 pending。

业务查询键：location + vehicle_model + bom_version + part_number
库内唯一约束：location + vehicle_model + bom_version + source_node_id
（同零件号若多节点，以 BOM source_node_id 区分；重导 BOM 后 id 可能变化）
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.audit_mixin import AuditUserMixin


class BomWeldingProcessBreakdownNode(AuditUserMixin, Base):
    """焊接工艺拆解主表（一节点一行）"""

    __tablename__ = "bom_welding_process_breakdown_node"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ---------- 业务维度（设计变更靠 bom_version 隔离） ----------
    location: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="采购基地。例：青岛",
    )
    customer_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="顾客名称（自 BOM 清单头冗余）。例：奇瑞公司",
    )
    vehicle_model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="项目/车型。例：T28",
    )
    bom_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="材料清单版本号（设计变更关键）。例：D/00",
    )

    # ---------- 辅助溯源（非业务关联键） ----------
    snapshot_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="生成时 BOM snapshot.id（辅助）",
    )
    source_node_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="生成时 bom_nodes.id（辅助；BOM 重导后可能失效）",
    )

    # ---------- 零件文本（对外按 part_number 关联） ----------
    part_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="零件号（行业匹配主键）",
    )
    part_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="零件名称",
    )
    level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="树层级。0=供货总成，1=一级分总成",
    )
    node_role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="节点角色：supply / structure / …",
    )
    parent_part_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="父节点零件号",
    )
    parent_part_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="父节点零件名称",
    )
    supply_part_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="所属供货总成零件号（L0 填自身）",
    )
    supply_part_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="所属供货总成名称",
    )

    # ---------- 装配用量（与明细 process_qty 含义不同） ----------
    assembly_qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="装配用量（套/件），来自 BOM 节点 qty；不是焊点个数",
    )
    assembly_qty_unit: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="装配用量单位。例：pcs",
    )

    weld_info_raw: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="焊接信息原文全文",
    )
    excel_row: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="来源 Excel 行号（辅助）",
    )
    parse_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ok",
        comment="解析状态：ok / partial / unparsed / anomaly",
    )
    process_line_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="有效工艺明细行数；L0 且 =0 表示计费异常",
    )
    qa_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="核对备注",
    )

    # ---------- 审核锁定 ----------
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

    lines: Mapped[list["BomWeldingProcessBreakdownLine"]] = relationship(
        "BomWeldingProcessBreakdownLine",
        back_populates="node",
        cascade="all, delete-orphan",
        order_by="BomWeldingProcessBreakdownLine.line_no",
    )

    __table_args__ = (
        UniqueConstraint(
            "location",
            "vehicle_model",
            "bom_version",
            "source_node_id",
            name="uix_weld_breakdown_node_scope_source",
        ),
        Index("ix_weld_breakdown_node_location", "location"),
        Index("ix_weld_breakdown_node_vehicle_model", "vehicle_model"),
        Index("ix_weld_breakdown_node_bom_version", "bom_version"),
        Index("ix_weld_breakdown_node_part_number", "part_number"),
        Index("ix_weld_breakdown_node_audit_status", "audit_status"),
        Index("ix_weld_breakdown_node_process_line_count", "process_line_count"),
        Index(
            "ix_weld_breakdown_node_scope",
            "location",
            "vehicle_model",
            "bom_version",
        ),
    )


class BomWeldingProcessBreakdownLine(AuditUserMixin, Base):
    """焊接工艺拆解明细（一节点 × 一种工艺一行；存单件过程量）"""

    __tablename__ = "bom_welding_process_breakdown_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    breakdown_node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bom_welding_process_breakdown_node.id", ondelete="CASCADE"),
        nullable=False,
        comment="主表 id（辅助外键）",
    )

    # 冗余零件号，便于按零件号导出/对账（业务关联不用本表 id）
    part_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="零件号冗余（与主表一致）",
    )

    line_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="同一节点内工艺序号，从 1 起",
    )
    process_token: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="原文拆解出的工艺词。例：焊点、凸焊、涂胶",
    )
    matched_span: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="原文命中片段",
    )

    # ---------- 单件过程量（未乘装配用量） ----------
    process_qty: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        comment="单件过程量（做 1 件该节点）；与 weld_info 数字一致，未乘 assembly_qty",
    )
    process_qty_unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="过程量单位。例：个、mm、条、m2",
    )
    process_qty_secondary: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4),
        nullable=True,
        comment="次要过程量（可空）。例：塞焊旁的 mm",
    )
    process_qty_secondary_unit: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="次要过程量单位",
    )

    standard_process_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment=(
            "标准焊接工艺名称（与 bom_welding_unit_price.item_name 对齐；"
            "枚举 WeldingStandardProcessName）。例：植/螺柱/凸焊、CO2焊缝"
        ),
    )
    standard_process_unit: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment=(
            "标准工艺目录单位（与焊接单价 unit 对齐；"
            "供核对 process_qty_unit）。例：个、CM、MM、平方"
        ),
    )
    map_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unmapped",
        comment="映射状态：ready / ambiguous / unmapped",
    )
    rollup_flag: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="own",
        comment="own / rolled_in_parent / orphan_child",
    )
    child_fastener_qty_sum: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4),
        nullable=True,
        comment="子件疑似被焊件用量合计（仅校验）",
    )
    qty_check_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="skipped",
        comment="match / mismatch / no_child / skipped",
    )
    qty_check_detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="用量校验说明",
    )

    node: Mapped["BomWeldingProcessBreakdownNode"] = relationship(
        "BomWeldingProcessBreakdownNode",
        back_populates="lines",
    )

    __table_args__ = (
        UniqueConstraint(
            "breakdown_node_id",
            "line_no",
            name="uix_weld_breakdown_line_node_line_no",
        ),
        Index("ix_weld_breakdown_line_part_number", "part_number"),
        Index("ix_weld_breakdown_line_process_token", "process_token"),
        Index("ix_weld_breakdown_line_standard_process_name", "standard_process_name"),
        Index("ix_weld_breakdown_line_map_status", "map_status"),
    )
