"""异步任务 Repository。"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.models.async_task import AsyncTask


class AsyncTaskRepository:
    """异步任务数据访问 — 只做 CRUD，不含业务判断。"""

    def get_by_task_id(self, db: Session, task_id: str) -> Optional[AsyncTask]:
        return db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first()

    def create(self, db: Session, data: dict) -> AsyncTask:
        record = AsyncTask(**data)
        db.add(record)
        db.flush()
        return record

    def update_fields(self, db: Session, record: AsyncTask, fields: dict) -> AsyncTask:
        for key, value in fields.items():
            setattr(record, key, value)
        record.updated_at = now()
        db.flush()
        return record

    def delete_older_than(self, db: Session, cutoff: datetime) -> int:
        """删除 updated_at 早于 cutoff 的任务，返回删除行数。"""
        query = db.query(AsyncTask).filter(AsyncTask.updated_at < cutoff)
        count = query.count()
        if count:
            query.delete(synchronize_session=False)
            db.flush()
        return count
