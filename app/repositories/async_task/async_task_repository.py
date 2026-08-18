"""异步任务 Repository（辅助库）。

读写形态与「类 Redis」进度语义对齐：
- 读：短生命周期 Session（查询进度快照）
- 写：Core Connection + AUTOCOMMIT（由 Service 打开连接后传入，立即可见）

禁止在 Repository 内自开引擎/改隔离级别；连接策略由 Service 负责。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Connection, delete, insert, update
from sqlalchemy.orm import Session

from app.models.async_task import AsyncTask


class AsyncTaskRepository:
    """异步任务数据访问 — 只做 SQL，不含节流/线程池等业务策略。"""

    def get_by_task_id(self, db: Session, task_id: str) -> Optional[AsyncTask]:
        return db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first()

    def insert_task(self, conn: Connection, values: dict[str, Any]) -> None:
        """AUTOCOMMIT 连接上插入一行。"""
        conn.execute(insert(AsyncTask).values(**values))

    def update_by_task_id(
        self,
        conn: Connection,
        task_id: str,
        values: dict[str, Any],
    ) -> None:
        """AUTOCOMMIT 连接上按 task_id 更新。"""
        conn.execute(
            update(AsyncTask)
            .where(AsyncTask.task_id == task_id)
            .values(**values)
        )

    def delete_older_than(self, conn: Connection, cutoff: datetime) -> int:
        """AUTOCOMMIT 连接上删除过期任务，返回删除行数。"""
        result = conn.execute(
            delete(AsyncTask).where(AsyncTask.updated_at < cutoff)
        )
        return int(result.rowcount or 0)
