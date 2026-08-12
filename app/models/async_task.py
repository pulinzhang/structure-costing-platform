"""异步任务表 — 落在辅助库（AuxiliaryBase），与主业务库隔离。"""

from sqlalchemy import Column, Index, Integer, String, Text

from app.database import AuxiliaryBase
from app.models.audit_mixin import AuditUserMixin


class AsyncTask(AuditUserMixin, AuxiliaryBase):
    """
    通用异步任务进度表。

    仅存轮询所需的最小字段：状态、进度、消息、结果 JSON。
    物理落在辅助库，进度写入不受主业务长事务写锁影响。
    """

    __tablename__ = "async_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键 ID")
    task_id = Column(String(36), nullable=False, unique=True, comment="任务 UUID")
    task_type = Column(
        String(64),
        nullable=False,
        default="generic",
        comment="任务类型，如 steel_price_policy_upload",
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending / running / completed / failed",
    )
    progress = Column(Integer, nullable=False, default=0, comment="进度 0-100")
    message = Column(String(500), nullable=False, default="", comment="当前阶段说明")
    result_json = Column(Text, nullable=True, comment="完成结果 JSON 字符串")
    operator_id = Column(Integer, nullable=True, comment="提交人用户 ID")
    operator_name = Column(String(50), nullable=True, comment="提交人显示名")

    __table_args__ = (
        Index("ix_async_tasks_task_id", "task_id"),
        Index("ix_async_tasks_task_type", "task_type"),
        Index("ix_async_tasks_status", "status"),
        Index("ix_async_tasks_updated_at", "updated_at"),
    )
