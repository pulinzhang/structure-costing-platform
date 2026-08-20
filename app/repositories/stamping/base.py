"""冲压工艺 Repository 公共基类。"""

from __future__ import annotations

import logging
from typing import Generic, Protocol, TypeVar

from sqlalchemy.orm import Session

from app.repositories.persist import apply_payload_fields, model_from_payload

logger = logging.getLogger("repository.stamping")


class HasId(Protocol):
    """带主键 id 的 ORM 模型协议（实例与类上都可访问 id）。"""

    id: int


T = TypeVar("T", bound=HasId)
TPayload = TypeVar("TPayload")


class BaseRepository(Generic[T, TPayload]):
    """Repository 基类，封装通用 CRUD 操作。"""

    def __init__(self, model: type[T]) -> None:
        self.model = model

    def get_by_id(self, db: Session, id: int) -> T | None:
        """根据 ID 查询单条记录"""
        return db.get(self.model, id)

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[T]:
        """查询所有记录（分页）"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, payload: TPayload) -> T:
        """写入会话；由 Service 提交事务。"""
        instance = model_from_payload(self.model, payload)
        db.add(instance)
        db.flush()
        db.refresh(instance)
        logger.info("创建记录: %s (id=%s)", self.model.__name__, instance.id)
        return instance

    def bulk_create(self, db: Session, payloads: list[TPayload]) -> list[T]:
        """批量写入会话；由 Service 提交事务。"""
        instances = [model_from_payload(self.model, payload) for payload in payloads]
        db.add_all(instances)
        logger.info("批量创建: %s x%s", self.model.__name__, len(instances))
        return instances

    def update(self, db: Session, id: int, payload: TPayload) -> T | None:
        """更新会话中的记录；由 Service 提交事务。"""
        instance = self.get_by_id(db, id)
        if instance is None:
            return None
        apply_payload_fields(
            instance,
            payload,
            skip=frozenset({"id", "created_by", "created_at"}),
        )
        db.flush()
        db.refresh(instance)
        logger.info("更新记录: %s (id=%s)", self.model.__name__, id)
        return instance

    def delete(self, db: Session, id: int) -> bool:
        """从会话删除；由 Service 提交事务。"""
        instance = self.get_by_id(db, id)
        if instance is None:
            return False
        db.delete(instance)
        db.flush()
        logger.info("删除记录: %s (id=%s)", self.model.__name__, id)
        return True
