"""
车身供货 BOM 数据模型（一级供应商视角）

两张表：
- bom_snapshots：一版材料清单的「头」（导入 Excel 的文档信息 + 基地）
- bom_nodes：三级树节点（邻接表），供货总成 L0 → 一级 L1 → 二级 L2

核价用途：
- snapshot 绑定「哪一基地、哪一车型、哪一版 BOM」
- node 提供结构用量与材料属性；与冲压工艺/钢价一律按零件号 part_number 匹配（不存 part_id）
- 月度核价结果另表存储（尚未建）

Excel 对照（材料清单典型列）：
  序号 | 总成内部号/零件号/名称/图示/单车用量/焊接信息
       | 一级内部号/零件号/名称/用量/焊接信息
       | 二级内部号/零件号/名称/图示/用量
       | 材料 | 料厚 | 厂家 | 重量 | 检具 | 备注
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, relationship

from app.database import Base
from app.models.audit_mixin import AuditUserMixin


class BomSnapshot(AuditUserMixin, Base):
    """
    BOM 清单版本头（主表）

    唯一键：location + vehicle_model + bom_version
    含义：同一采购基地、同一车型、同一清单版本只有一份生效树。
    覆盖导入时会删旧树再写新树；Excel 原件因带时间戳文件名而保留历史。

    另含 AuditUserMixin：created_at / created_by / updated_at / updated_by
    """

    __tablename__ = "bom_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")

    # ---------- 业务主键维度（核价/钢价匹配必用） ----------
    location = Column(
        String(50),
        nullable=False,
        comment="采购基地（导入必选，非 Excel 字段）。例：大连、芜湖、鄂尔多斯、青岛。与钢价/冲压零件基地对齐",
    )
    vehicle_model = Column(
        String(50),
        nullable=False,
        comment="项目/车型代号。来自 Excel 头「项目代号」，例：T28",
    )
    bom_version = Column(
        String(20),
        nullable=False,
        comment="材料清单版本号。来自 Excel 头「版本」，例：D/00；解析不到时默认 V1",
    )

    # ---------- Excel 文档头信息（展示/溯源，不参与钢价匹配） ----------
    product_category = Column(
        String(50),
        nullable=True,
        comment="产品类别。来自 Excel 头「产品类别」，例：车身件",
    )
    customer_name = Column(
        String(100),
        nullable=True,
        comment="顾客/主机厂名称。来自 Excel 头「顾客名称」，例：奇瑞公司",
    )
    stage = Column(
        String(30),
        nullable=False,
        default="initial",
        comment="清单阶段。initial=初始清单，mass=批量生产清单（Excel 勾选框解析）",
    )
    doc_no = Column(
        String(50),
        nullable=True,
        comment="单据编号。来自 Excel 头「编号」，可空",
    )
    prepare_dept = Column(
        String(100),
        nullable=True,
        comment="编制部门。来自 Excel 头「编制部门」，例：技术中心",
    )
    doc_date = Column(
        Date,
        nullable=True,
        comment="编制日期。来自 Excel 头「编制日期」",
    )
    revision_date = Column(
        Date,
        nullable=True,
        comment="修订日期。来自 Excel 头「修订日期」",
    )
    title = Column(
        String(200),
        nullable=True,
        comment="清单标题。来自 Excel 第 1 行，例：T28项目产品材料清单",
    )

    # ---------- 源文件落盘（防扯皮） ----------
    source_filename = Column(
        String(255),
        nullable=False,
        comment="上传时的原始 Excel 文件名（用户侧名称）",
    )
    source_sheet_name = Column(
        String(100),
        nullable=True,
        comment="解析所用工作表名（Excel 表页）。例：材料清单",
    )
    source_file_path = Column(
        String(500),
        nullable=True,
        comment="服务器落盘相对路径（相对 UPLOAD_DIR）。例：bom/青岛/T28/D_00/青岛_T28_D_00_时间戳_原名.xlsx；通过 /uploads/ 访问",
    )
    source_file_hash = Column(
        String(64),
        nullable=True,
        comment="源 Excel 文件内容 SHA256（64 位 hex），用于完整性校验/去重比对",
    )

    # ---------- 状态 ----------
    status = Column(
        String(20),
        nullable=False,
        default="active",
        comment="清单状态：draft=草稿，active=生效，archived=归档。导入默认为 active",
    )
    remark = Column(
        Text,
        nullable=True,
        comment="清单级备注（人工备注，非 Excel 行备注）",
    )

    nodes: Mapped[list["BomNode"]] = relationship(
        "BomNode",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "location",
            "vehicle_model",
            "bom_version",
            name="uix_bom_snapshot_location_model_version",
        ),
        Index("ix_bom_snapshot_location", "location"),
        Index("ix_bom_snapshot_vehicle_model", "vehicle_model"),
        Index("ix_bom_snapshot_status", "status"),
    )


class BomNode(AuditUserMixin, Base):
    """
    BOM 树节点（子表，邻接表）

    parent_id 指向父节点；供货总成 L0 的 parent_id 为空。
    同一 snapshot 下构成整棵三级树。

    node_role 决定核价路径（冲焊件供应商域，不含电子/电气品类）：
    - supply：供货总成（对外报价单元）
    - structure：中间结构（有子件，自身不算材料）
    - make：自制冲压板料叶子（走钢价）
    - buy：外购标准件（螺栓/螺母等）
    - consumable：胶 / 焊丝等耗材（用量常为 mm）

    零件名称中的「电机」「线束」等字样通常描述安装对象或关联功能，
    不代表本企业供应电器；角色判定不以电器关键词为准。

    另含 AuditUserMixin：created_at / created_by / updated_at / updated_by
    """

    __tablename__ = "bom_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")

    # ---------- 树结构 ----------
    snapshot_id = Column(
        Integer,
        ForeignKey("bom_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属清单版本（外键 → bom_snapshots.id）。删清单时级联删节点",
    )
    parent_id = Column(
        Integer,
        ForeignKey("bom_nodes.id", ondelete="CASCADE"),
        nullable=True,
        comment="父节点 ID（外键 → bom_nodes.id）。L0 供货总成为 NULL；删父节点时级联删子树",
    )
    level = Column(
        SmallInteger,
        nullable=False,
        comment="树层级。0=供货总成，1=一级子件，2=二级子件（对应 Excel 三级列组）",
    )
    sort_no = Column(
        Integer,
        nullable=False,
        default=0,
        comment="导入顺序号（全局递增，用于还原 Excel 行序/同级排序）",
    )
    seq_no = Column(
        Integer,
        nullable=True,
        comment="Excel「序号」列。通常仅 L0 有值，例：1、2、3",
    )

    # ---------- 零件标识（来自 Excel 对应层级列） ----------
    internal_number = Column(
        String(50),
        nullable=True,
        comment="内部号。L0←总成内部号，L1←一级内部号，L2←二级内部号。例：ACA610、ACA610001",
    )
    part_number = Column(
        String(50),
        nullable=False,
        comment=(
            "零件号（行业匹配主键）。"
            "与冲压工艺、钢价等一律按零件号关联，不存外键 part_id。"
            "L0←总成零件号，L1←一级零件号，L2←二级零件号。例：501006873AA"
        ),
    )
    part_name = Column(
        String(200),
        nullable=True,
        comment="零件名称。对应各层级「零件名称」列。例：流水槽加强梁总成",
    )

    # ---------- 用量（相对父件；单车用量需沿树连乘） ----------
    qty = Column(
        Numeric(12, 4),
        nullable=True,
        comment="相对父件用量数值。板料/件多为整数；胶可能为长度数值。缺省解析为 1",
    )
    qty_unit = Column(
        String(20),
        nullable=False,
        default="pcs",
        comment="用量单位。pcs=件数；mm=长度（结构胶等）。影响核价是否走钢价公式",
    )
    qty_text = Column(
        String(50),
        nullable=True,
        comment="用量原文（保留 Excel 写法）。例：1、2、1550mm",
    )

    # ---------- 角色 / 报价边界 ----------
    node_role = Column(
        String(20),
        nullable=False,
        comment=(
            "节点角色（导入自动推断，可人工校正）："
            "supply=供货总成；structure=中间结构；"
            "make=自制冲压板料；buy=外购标准件；consumable=耗材/胶。"
            "冲焊件业务域不含电子/电气品类。"
        ),
    )
    is_supply_unit = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否对外供货/报价单元。一般为 L0=True；月度汇总、对账以该标记为准",
    )

    # ---------- 材料属性（主要挂在叶子；有二级时属性在二级） ----------
    material = Column(
        String(50),
        nullable=True,
        comment="材质/牌号。来自 Excel「材料」列。例：DC01、HC180YD+Z、SWRCH22A。自制件用于匹配钢价",
    )
    thickness_mm = Column(
        Numeric(10, 4),
        nullable=True,
        comment="料厚毫米数（解析值）。从「料厚」列 T=1.2 解析；标准件 M6 等无法解析则为空",
    )
    thickness_text = Column(
        String(50),
        nullable=True,
        comment="料厚/规格原文。例：T=1.2、M6、M6x16、发泡料（环氧树脂等）",
    )
    material_mill = Column(
        String(100),
        nullable=True,
        comment="材料厂家。来自 Excel「材料厂家」列，可空",
    )
    part_weight = Column(
        Numeric(12, 4),
        nullable=True,
        comment="单件重量(kg)。来自 Excel「单件重量」。Phase1 材料费可用净重估算",
    )
    gauge_developed = Column(
        String(10),
        nullable=True,
        comment="检具是否开发。来自 Excel「检具是否开发」，例：是/否",
    )

    # ---------- 工艺/商务附属 ----------
    weld_info = Column(
        Text,
        nullable=True,
        comment="焊接/涂胶等信息原文。L0←总成焊接信息列，L1←一级焊接信息列。例：焊点：4 / 凸焊：2",
    )
    remark = Column(
        Text,
        nullable=True,
        comment="行备注。来自 Excel「备注」。例：沿用T26、凸焊总成供货",
    )
    sketch_url = Column(
        String(500),
        nullable=True,
        comment=(
            "图示相对路径（相对 UPLOAD_DIR）。"
            "E列总成图示→L0；"
            "P列单件图示→有L2归L2，无L2时归L1（一级零件图）；"
            "例：bom/青岛/T28/D_00/sketches/12_501006875AA.png；访问 /uploads/{sketch_url}"
        ),
    )

    # ---------- Excel 单元格溯源（防扯皮；与钢价四件套对齐） ----------
    excel_filename = Column(
        String(255),
        nullable=True,
        comment="导入时原始 Excel 文件名快照（与清单头 source_filename 一致）",
    )
    excel_sheet_name = Column(
        String(100),
        nullable=True,
        comment="来源工作表名。例：材料清单",
    )
    excel_row = Column(
        Integer,
        nullable=True,
        comment="来源 Excel 行号（1-based，与 Excel 界面行号一致）",
    )
    excel_part_col = Column(
        Integer,
        nullable=True,
        comment="本节点零件号所在列号（1-based）。L0=3，L1=9，L2=14",
    )

    snapshot: Mapped["BomSnapshot"] = relationship("BomSnapshot", back_populates="nodes")
    parent: Mapped["BomNode | None"] = relationship(
        "BomNode",
        remote_side=[id],
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children: Mapped[list["BomNode"]] = relationship(
        "BomNode",
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id],
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_bom_node_snapshot_parent", "snapshot_id", "parent_id"),
        Index("ix_bom_node_snapshot_level", "snapshot_id", "level"),
        Index("ix_bom_node_snapshot_part_number", "snapshot_id", "part_number"),
        Index("ix_bom_node_snapshot_supply", "snapshot_id", "is_supply_unit"),
    )
