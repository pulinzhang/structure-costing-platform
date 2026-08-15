"""冲压工艺 Repository 公共基类。"""

from __future__ import annotations

import logging
from typing import Any, Generic, Protocol, TypeVar

from sqlalchemy.orm import Session

logger = logging.getLogger("repository.stamping")


class HasId(Protocol):
    """带主键 id 的 ORM 模型协议（实例与类上都可访问 id）。"""

    id: int


T = TypeVar("T", bound=HasId)


class BaseRepository(Generic[T]):
    """Repository 基类，封装通用 CRUD 操作"""

    def __init__(self, model: type[T]) -> None:
        self.model = model

    def get_by_id(self, db: Session, id: int) -> T | None:
        """根据 ID 查询单条记录"""
        return db.get(self.model, id)

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[T]:
        """查询所有记录（分页）"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, data: dict[str, Any]) -> T:
        """创建单条记录"""
        instance = self.model(**data)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        logger.info("创建记录: %s (id=%s)", self.model.__name__, instance.id)
        return instance

    def bulk_create(self, db: Session, data_list: list[dict[str, Any]]) -> list[T]:
        """批量创建记录（不提交事务，由调用方管理）"""
        instances = [self.model(**data) for data in data_list]
        db.add_all(instances)
        logger.info("批量创建: %s x%s", self.model.__name__, len(instances))
        return instances

    def update(self, db: Session, id: int, update_data: dict[str, Any]) -> T | None:
        """更新记录"""
        instance = self.get_by_id(db, id)
        if instance is None:
            return None
        for key, value in update_data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        db.commit()
        db.refresh(instance)
        logger.info("更新记录: %s (id=%s)", self.model.__name__, id)
        return instance

    def delete(self, db: Session, id: int) -> bool:
        """删除记录"""
        instance = self.get_by_id(db, id)
        if instance is None:
            return False
        db.delete(instance)
        db.commit()
        logger.info("删除记录: %s (id=%s)", self.model.__name__, id)
        return True
