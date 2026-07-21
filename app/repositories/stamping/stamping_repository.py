"""
冲压工艺 Repository
数据访问层，只负责与数据库交互
"""

import logging
from typing import List, Optional, Dict, Any, Tuple, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.models import StampingPart, StampingProcess


logger = logging.getLogger("repository.stamping")

# 泛型：表示任意 ORM 模型类
T = TypeVar("T")


class BaseRepository:
    """Repository 基类，封装通用 CRUD 操作"""

    def __init__(self, model: Type[T]):
        self.model = model

    def get_by_id(self, db: Session, id: int) -> Optional[T]:
        """根据 ID 查询单条记录"""
        return db.query(self.model).filter(self.model.id == id).first()

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[T]:
        """查询所有记录（分页）"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, data: Dict[str, Any]) -> T:
        """创建单条记录"""
        instance = self.model(**data)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        logger.info(f"创建记录: {self.model.__name__} (id={instance.id})")
        return instance

    def bulk_create(self, db: Session, data_list: List[Dict[str, Any]]) -> List[T]:
        """批量创建记录"""
        instances = [self.model(**data) for data in data_list]
        db.add_all(instances)
        db.commit()
        for instance in instances:
            db.refresh(instance)
        logger.info(f"批量创建: {self.model.__name__} x{len(instances)}")
        return instances

    def update(self, db: Session, id: int, update_data: Dict[str, Any]) -> Optional[T]:
        """更新记录"""
        instance = self.get_by_id(db, id)
        if not instance:
            return None
        for key, value in update_data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        db.commit()
        db.refresh(instance)
        logger.info(f"更新记录: {self.model.__name__} (id={id})")
        return instance

    def delete(self, db: Session, id: int) -> bool:
        """删除记录"""
        instance = self.get_by_id(db, id)
        if not instance:
            return False
        db.delete(instance)
        db.commit()
        logger.info(f"删除记录: {self.model.__name__} (id={id})")
        return True


class StampingPartRepository:
    """零件数据访问"""

    def get_by_id(self, db: Session, part_id: int) -> Optional[StampingPart]:
        from sqlalchemy.orm import selectinload
        return (
            db.query(StampingPart)
            .options(selectinload(StampingPart.processes))
            .filter(StampingPart.id == part_id)
            .first()
        )

    def get_by_part_number(self, db: Session, part_number: str) -> Optional[StampingPart]:
        return db.query(StampingPart).filter(StampingPart.part_number == part_number).first()

    def filter_by_vehicle_version(
        self,
        db: Session,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
    ) -> Tuple[List[StampingPart], int]:
        """查询零件，返回 (结果列表, 总数)"""
        q = db.query(StampingPart)
        if vehicle_model is not None:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPart.version == version)
        if part_number:
            q = q.filter(StampingPart.part_number.like(f"%{part_number}%"))
        if part_name:
            q = q.filter(StampingPart.part_name.like(f"%{part_name}%"))

        total = q.count()
        from sqlalchemy.orm import selectinload
        parts = (
            q.options(selectinload(StampingPart.processes))
            .order_by(StampingPart.seq_no)
            .all()
        )
        return parts, total

    def paginate(
        self,
        db: Session,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StampingPart], int]:
        """分页查询零件"""
        q = db.query(StampingPart)
        if vehicle_model is not None:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPart.version == version)
        if part_number:
            q = q.filter(StampingPart.part_number.like(f"%{part_number}%"))
        if part_name:
            q = q.filter(StampingPart.part_name.like(f"%{part_name}%"))

        total = q.count()
        parts = q.order_by(StampingPart.seq_no).offset(skip).limit(limit).all()
        return parts, total

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[StampingPart]:
        return db.query(StampingPart).offset(skip).limit(limit).all()

    def create(self, db: Session, part_data: Dict[str, Any]) -> StampingPart:
        part = StampingPart(**part_data)
        db.add(part)
        db.commit()
        db.refresh(part)
        logger.info(f"创建零件: {part.part_number} (id={part.id})")
        return part

    def bulk_create(self, db: Session, parts_data: List[Dict[str, Any]]) -> List[StampingPart]:
        parts = [StampingPart(**data) for data in parts_data]
        db.add_all(parts)
        db.commit()
        for part in parts:
            db.refresh(part)
        logger.info(f"批量创建零件: {len(parts)} 个")
        return parts

    def update(self, db: Session, part_id: int, update_data: Dict[str, Any]) -> Optional[StampingPart]:
        part = self.get_by_id(db, part_id)
        if not part:
            return None
        for key, value in update_data.items():
            if hasattr(part, key):
                setattr(part, key, value)
        db.commit()
        db.refresh(part)
        logger.info(f"更新零件: id={part_id}")
        return part

    def delete(self, db: Session, part_id: int) -> bool:
        part = self.get_by_id(db, part_id)
        if not part:
            return False
        db.query(StampingProcess).filter(StampingProcess.part_id == part_id).delete()
        db.delete(part)
        db.commit()
        logger.info(f"删除零件: id={part_id}")
        return True

    def get_all_by_vehicle_version(self, db: Session, vehicle_model: str, version: str) -> List[StampingPart]:
        """获取指定车型版本的所有零件（不分页）"""
        return db.query(StampingPart).filter(
            StampingPart.vehicle_model == vehicle_model,
            StampingPart.version == version,
        ).all()

    def delete_by_vehicle_version(self, db: Session, vehicle_model: str, version: str) -> int:
        """删除指定车型版本的全部零件和工序"""
        parts = self.get_all_by_vehicle_version(db, vehicle_model, version)
        count = len(parts)
        for part in parts:
            db.query(StampingProcess).filter(StampingProcess.part_id == part.id).delete()
            db.delete(part)
        db.commit()
        logger.info(f"删除车型版本: {vehicle_model}/{version}, 共 {count} 个零件")
        return count

    def get_id_map_by_vehicle_version(self, db: Session, vehicle_model: str, version: str) -> Dict[str, int]:
        """获取零件号到 ID 的映射"""
        parts = self.get_all_by_vehicle_version(db, vehicle_model, version)
        return {p.part_number: p.id for p in parts if p.part_number}

    def count_processes_by_part_ids(self, db: Session, part_ids: List[int]) -> Dict[int, int]:
        """
        批量统计每个零件的工序数（一次 SQL, IN 子查询）。
        返回 {part_id: process_count}，缺省为 0。
        """
        if not part_ids:
            return {}
        rows = (
            db.query(StampingProcess.part_id, func.count(StampingProcess.id))
            .filter(StampingProcess.part_id.in_(part_ids))
            .group_by(StampingProcess.part_id)
            .all()
        )
        counts = {pid: cnt for pid, cnt in rows}
        return {pid: counts.get(pid, 0) for pid in part_ids}

    def get_filter_options(self, db: Session) -> Dict[str, List[str]]:
        """
        获取筛选下拉框的可选值（车型列表 & 版本列表）。
        返回 {'vehicle_models': [...], 'versions': [...]}。
        """
        vehicle_models = (
            db.query(StampingPart.vehicle_model)
            .distinct()
            .filter(StampingPart.vehicle_model.isnot(None))
            .order_by(StampingPart.vehicle_model)
            .all()
        )
        versions = (
            db.query(StampingPart.version)
            .distinct()
            .filter(StampingPart.version.isnot(None))
            .order_by(StampingPart.version)
            .all()
        )
        return {
            "vehicle_models": [r[0] for r in vehicle_models],
            "versions": [r[0] for r in versions],
        }


class StampingProcessRepository:
    """工序数据访问"""

    def get_by_id(self, db: Session, process_id: int) -> Optional[StampingProcess]:
        return db.query(StampingProcess).filter(StampingProcess.id == process_id).first()

    def get_by_part_id(self, db: Session, part_id: int) -> List[StampingProcess]:
        return (
            db.query(StampingProcess)
            .filter(StampingProcess.part_id == part_id)
            .order_by(StampingProcess.process_order)
            .all()
        )

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[StampingProcess]:
        return db.query(StampingProcess).offset(skip).limit(limit).all()

    def create(self, db: Session, process_data: Dict[str, Any]) -> StampingProcess:
        process = StampingProcess(**process_data)
        db.add(process)
        db.commit()
        db.refresh(process)
        logger.info(f"创建工序: id={process.id}")
        return process

    def bulk_create(self, db: Session, processes_data: List[Dict[str, Any]]) -> List[StampingProcess]:
        processes = [StampingProcess(**data) for data in processes_data]
        db.add_all(processes)
        db.commit()
        for p in processes:
            db.refresh(p)
        logger.info(f"批量创建工序: {len(processes)} 个")
        return processes

    def update(self, db: Session, process_id: int, update_data: Dict[str, Any]) -> Optional[StampingProcess]:
        process = self.get_by_id(db, process_id)
        if not process:
            return None
        for key, value in update_data.items():
            if hasattr(process, key):
                setattr(process, key, value)
        db.commit()
        db.refresh(process)
        logger.info(f"更新工序: id={process_id}")
        return process

    def delete(self, db: Session, process_id: int) -> bool:
        process = self.get_by_id(db, process_id)
        if not process:
            return False
        db.delete(process)
        db.commit()
        logger.info(f"删除工序: id={process_id}")
        return True

    def delete_by_part_ids(self, db: Session, part_ids: List[int]) -> int:
        count = db.query(StampingProcess).filter(StampingProcess.part_id.in_(part_ids)).delete(
            synchronize_session=False
        )
        db.commit()
        logger.info(f"删除工序: {count} 个 (part_ids={part_ids})")
        return count
