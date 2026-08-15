"""冲压工序数据访问。"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import StampingProcess

logger = logging.getLogger("repository.stamping.process")


class StampingProcessRepository:
    """工序数据访问"""

    def count_all(self, db: Session) -> int:
        """工序总数。"""
        return db.query(StampingProcess).count()

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
