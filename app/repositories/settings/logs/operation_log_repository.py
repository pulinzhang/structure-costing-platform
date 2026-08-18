"""操作日志 Repository。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.settings import OperationLog


class OperationLogRepository:
    """操作日志数据访问。"""

    def create(self, db: Session, data: dict[str, Any]) -> OperationLog:
        row = OperationLog(**data)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def paginate(
        self,
        db: Session,
        *,
        username: str | None = None,
        module: str | None = None,
        action: str | None = None,
        method: str | None = None,
        success: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[OperationLog], int]:
        q = db.query(OperationLog)
        if username:
            q = q.filter(OperationLog.username.like(f"%{username.strip()}%"))
        if module:
            q = q.filter(OperationLog.module == module.strip())
        if action:
            q = q.filter(OperationLog.action == action.strip())
        if method:
            q = q.filter(OperationLog.method == method.strip().upper())
        if success is not None:
            q = q.filter(OperationLog.success == success)
        if created_from is not None:
            q = q.filter(OperationLog.created_at >= created_from)
        if created_to is not None:
            q = q.filter(OperationLog.created_at <= created_to)

        total = q.count()
        rows = (
            q.order_by(OperationLog.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def list_for_export(
        self,
        db: Session,
        *,
        username: str | None = None,
        module: str | None = None,
        action: str | None = None,
        method: str | None = None,
        success: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 10000,
    ) -> list[OperationLog]:
        q = db.query(OperationLog)
        if username:
            q = q.filter(OperationLog.username.like(f"%{username.strip()}%"))
        if module:
            q = q.filter(OperationLog.module == module.strip())
        if action:
            q = q.filter(OperationLog.action == action.strip())
        if method:
            q = q.filter(OperationLog.method == method.strip().upper())
        if success is not None:
            q = q.filter(OperationLog.success == success)
        if created_from is not None:
            q = q.filter(OperationLog.created_at >= created_from)
        if created_to is not None:
            q = q.filter(OperationLog.created_at <= created_to)
        return (
            q.order_by(OperationLog.id.desc())
            .limit(limit)
            .all()
        )

    def list_filter_options(self, db: Session) -> dict[str, list[str]]:
        modules = [
            r[0]
            for r in db.query(OperationLog.module)
            .filter(OperationLog.module.isnot(None))
            .distinct()
            .order_by(OperationLog.module)
            .all()
            if r[0]
        ]
        actions = [
            r[0]
            for r in db.query(OperationLog.action)
            .distinct()
            .order_by(OperationLog.action)
            .all()
            if r[0]
        ]
        methods = [
            r[0]
            for r in db.query(OperationLog.method)
            .distinct()
            .order_by(OperationLog.method)
            .all()
            if r[0]
        ]
        return {"modules": modules, "actions": actions, "methods": methods}
