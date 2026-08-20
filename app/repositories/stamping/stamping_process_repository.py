"""冲压工序数据访问。"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import StampingProcess
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.stamping_upload_dto import ProcessData, StampingProcessPatch

logger = logging.getLogger("repository.stamping.process")


class StampingProcessRepository:
    """工序数据访问"""

    def count_all(self, db: Session) -> int:
        """工序总数。"""
        return db.query(StampingProcess).count()

    def count_by_part_location(self, db: Session, location: str | None = None) -> int:
        """按零件生产基地统计工序数；location 为空则全库。"""
        from app.models import StampingPart

        q = db.query(StampingProcess).join(
            StampingPart, StampingProcess.part_id == StampingPart.id
        )
        if location:
            q = q.filter(StampingPart.location == location)
        return int(q.count())

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

    def list_by_scope(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
    ) -> List[StampingProcess]:
        """按基地 + 冲压工厂 + 车型 + 版本查询工序（含所属零件）。"""
        from sqlalchemy.orm import contains_eager

        from app.models import StampingPart

        return (
            db.query(StampingProcess)
            .join(StampingPart, StampingProcess.part_id == StampingPart.id)
            .options(contains_eager(StampingProcess.part))
            .filter(
                StampingPart.location == location,
                StampingPart.stamping_supplier == stamping_supplier,
                StampingPart.vehicle_model == vehicle_model,
                StampingPart.version == version,
            )
            .all()
        )

    def create(self, db: Session, process_data: ProcessData) -> StampingProcess:
        process = model_from_payload(StampingProcess, process_data)
        db.add(process)
        db.flush()
        db.refresh(process)
        logger.info("创建工序: id=%s", process.id)
        return process

    def bulk_create(self, db: Session, processes_data: List[ProcessData]) -> List[StampingProcess]:
        processes = [model_from_payload(StampingProcess, data) for data in processes_data]
        db.add_all(processes)
        logger.info("批量创建工序: %s 个", len(processes))
        return processes

    def update(
        self, db: Session, process_id: int, update_data: StampingProcessPatch
    ) -> Optional[StampingProcess]:
        process = self.get_by_id(db, process_id)
        if not process:
            return None
        apply_payload_fields(
            process,
            update_data,
            skip=frozenset({"id", "created_by", "created_at"}),
        )
        db.flush()
        db.refresh(process)
        logger.info("更新工序: id=%s", process_id)
        return process

    def delete(self, db: Session, process_id: int) -> bool:
        process = self.get_by_id(db, process_id)
        if not process:
            return False
        db.delete(process)
        db.flush()
        logger.info(f"删除工序: id={process_id}")
        return True

    def delete_by_part_ids(self, db: Session, part_ids: List[int]) -> int:
        count = db.query(StampingProcess).filter(StampingProcess.part_id.in_(part_ids)).delete(
            synchronize_session=False
        )
        db.flush()
        logger.info(f"删除工序: {count} 个 (part_ids={part_ids})")
        return count
