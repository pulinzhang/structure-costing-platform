"""
冲压工艺 Repository
数据访问层，只负责与数据库交互
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.models import StampingPart, StampingProcess


logger = logging.getLogger("repository.stamping")


class StampingPartRepository:
    """零件数据访问"""

    def get_by_id(self, db: Session, part_id: int) -> Optional[StampingPart]:
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
