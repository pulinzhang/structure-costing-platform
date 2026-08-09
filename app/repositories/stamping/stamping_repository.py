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

    def paginate(
        self,
        db: Session,
        location: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StampingPart], int]:
        """分页查询零件"""
        q = db.query(StampingPart)
        if location is not None:
            q = q.filter(StampingPart.location == location)
        if stamping_supplier is not None:
            q = q.filter(StampingPart.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPart.version == version)
        if part_number:
            q = q.filter(StampingPart.part_number.like(f"%{part_number}%"))
        if part_name:
            q = q.filter(StampingPart.part_name.like(f"%{part_name}%"))

        total = q.count()
        parts = q.order_by(StampingPart.id).offset(skip).limit(limit).all()
        return parts, total

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
        """获取筛选下拉框的可选值（基地、供应商、车型、版本）。"""
        locations = (
            db.query(StampingPart.location)
            .distinct()
            .filter(StampingPart.location.isnot(None))
            .order_by(StampingPart.location)
            .all()
        )
        suppliers = (
            db.query(StampingPart.stamping_supplier)
            .distinct()
            .filter(StampingPart.stamping_supplier.isnot(None))
            .order_by(StampingPart.stamping_supplier)
            .all()
        )
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
            "locations": [r[0] for r in locations],
            "stamping_suppliers": [r[0] for r in suppliers],
            "vehicle_models": [r[0] for r in vehicle_models],
            "versions": [r[0] for r in versions],
        }

    # ── 以下方法由调用方管理事务，Repository 层不 commit ──

    def bulk_create(self, db: Session, parts_data: List[Dict[str, Any]]) -> List[StampingPart]:
        """批量创建零件（调用方须在 Service 层 flush/commit）"""
        parts = [StampingPart(**data) for data in parts_data]
        db.add_all(parts)
        logger.info(f"批量创建零件: {len(parts)} 个")
        return parts

    def get_id_map_by_vehicle_version(self, db: Session, vehicle_model: str, version: str) -> Dict[str, int]:
        """获取零件号到 ID 的映射（调用方须在 Service 层 flush 后调用）"""
        parts = (
            db.query(StampingPart)
            .filter(
                StampingPart.vehicle_model == vehicle_model,
                StampingPart.version == version,
            )
            .all()
        )
        return {p.part_number: p.id for p in parts if p.part_number}

    def delete_by_vehicle_version(self, db: Session, vehicle_model: str, version: str) -> int:
        """删除指定车型版本的全部零件和工序（调用方须在 Service 层 commit）"""
        parts = (
            db.query(StampingPart)
            .filter(
                StampingPart.vehicle_model == vehicle_model,
                StampingPart.version == version,
            )
            .all()
        )
        count = len(parts)
        for part in parts:
            db.query(StampingProcess).filter(StampingProcess.part_id == part.id).delete()
            db.delete(part)
        logger.info(f"删除车型版本: {vehicle_model}/{version}, 共 {count} 个零件")
        return count

    def delete(self, db: Session, part_id: int) -> bool:
        """删除零件及关联工序（调用方须在 Service 层 commit）"""
        part = self.get_by_id(db, part_id)
        if not part:
            return False
        db.query(StampingProcess).filter(StampingProcess.part_id == part_id).delete()
        db.delete(part)
        logger.info(f"删除零件: id={part_id}")
        return True


class StampingProcessRepository:
    """工序数据访问"""

    def get_by_id(self, db: Session, process_id: int) -> Optional[StampingProcess]:
        return db.query(StampingProcess).filter(StampingProcess.id == process_id).first()

    def bulk_create(self, db: Session, processes_data: List[Dict[str, Any]]) -> List[StampingProcess]:
        """批量创建工序（调用方须在 Service 层 flush/commit）"""
        processes = [StampingProcess(**data) for data in processes_data]
        db.add_all(processes)
        logger.info(f"批量创建工序: {len(processes)} 个")
        return processes

    def update(self, db: Session, process_id: int, update_data: Dict[str, Any]) -> Optional[StampingProcess]:
        """更新工序（调用方须在 Service 层 commit）"""
        process = self.get_by_id(db, process_id)
        if not process:
            return None
        for key, value in update_data.items():
            if hasattr(process, key):
                setattr(process, key, value)
        logger.info(f"更新工序: id={process_id}")
        return process
