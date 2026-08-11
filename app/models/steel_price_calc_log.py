"""钢材价格计算批次日志模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, text

from app.database import Base


class SteelPriceCalcLog(Base):
    """
    钢价计算批次日志

    一次「开始计算」先写入 processing 行作为期别锁，结束后更新为终态；
    detail_text 记录完整过程（含错误）。
    """

    __tablename__ = "steel_price_calc_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键 ID")
    calc_batch_id = Column(String(64), nullable=False, unique=True, comment="计算批次号")

    year = Column(Integer, nullable=False, comment="核价年度")
    month = Column(Integer, nullable=False, comment="核价月份")
    location = Column(String(50), nullable=False, comment="生产基地")
    stamping_supplier = Column(String(50), nullable=True, comment="冲压工厂（筛选）")
    vehicle_model = Column(String(50), nullable=True, comment="配套车型（筛选）")

    status = Column(
        String(20),
        nullable=False,
        default="failed",
        comment="批次状态：processing / success / partial / failed",
    )

    material_count = Column(Integer, nullable=False, default=0, comment="材料厚度规格数")
    enriched_count = Column(Integer, nullable=False, default=0, comment="命中基价展开行数")
    no_base_count = Column(Integer, nullable=False, default=0, comment="无基价规格数")
    created_count = Column(Integer, nullable=False, default=0, comment="新增结果条数")
    updated_count = Column(Integer, nullable=False, default=0, comment="更新结果条数")
    skipped_approved_count = Column(
        Integer, nullable=False, default=0, comment="跳过已审核条数"
    )
    failed_count = Column(Integer, nullable=False, default=0, comment="落库失败条数")

    detail_text = Column(
        Text,
        nullable=False,
        default="",
        comment="计算过程全文（步骤、命中、错误均记录）",
    )

    started_at = Column(DateTime, nullable=False, comment="计算开始时间")
    finished_at = Column(DateTime, nullable=True, comment="计算结束时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")

    __table_args__ = (
        Index("ix_steel_price_calc_log_batch", "calc_batch_id"),
        Index("ix_steel_price_calc_log_year_month", "year", "month"),
        Index("ix_steel_price_calc_log_location", "location"),
        Index("ix_steel_price_calc_log_status", "status"),
        Index("ix_steel_price_calc_log_started_at", "started_at"),
        # 同一年度+月份+基地同时只允许一条 processing（SQLite 部分唯一索引）
        Index(
            "uq_steel_price_calc_processing",
            "year",
            "month",
            "location",
            unique=True,
            sqlite_where=text("status = 'processing'"),
        ),
    )
