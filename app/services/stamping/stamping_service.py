"""
冲压工艺 Service
业务逻辑层，处理业务规则和事务
"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.repositories.stamping.stamping_repository import StampingPartRepository
from app.schemas.stamping import StampingPartQuery, StampingPartListResponse, StampingPartResponse


logger = logging.getLogger("service.stamping")


class StampingPartService:
    """零件业务逻辑"""

    def __init__(self):
        self.repository = StampingPartRepository()

    def list_parts(self, db: Session, query: StampingPartQuery) -> tuple[List[Dict[str, Any]], int]:
        """获取零件列表（不含工序详情，含工序统计数 process_count）"""
        skip = (query.page - 1) * query.size
        parts, total = self.repository.paginate(
            db,
            vehicle_model=query.vehicle_model,
            version=query.version,
            part_number=query.part_number,
            part_name=query.part_name,
            skip=skip,
            limit=query.size,
        )
        # 一次聚合查询补齐每行工序数（避免 ORM lazy load 触发 N+1）
        part_ids = [p.id for p in parts]
        process_counts = self.repository.count_processes_by_part_ids(db, part_ids)

        rows = []
        for p in parts:
            row = StampingPartListResponse.model_validate(p).model_dump()
            row["process_count"] = process_counts.get(p.id, 0)
            rows.append(row)
        return rows, total

    def get_by_id(self, db: Session, part_id: int) -> Optional[Dict[str, Any]]:
        """获取单个零件"""
        part = self.repository.get_by_id(db, part_id)
        if not part:
            return None
        return StampingPartResponse.model_validate(part).model_dump()

    def delete(self, db: Session, part_id: int) -> bool:
        """删除零件"""
        return self.repository.delete(db, part_id)

    def get_id_map(self, db: Session, vehicle_model: str, version: str) -> Dict[str, int]:
        """获取零件号映射"""
        return self.repository.get_id_map_by_vehicle_version(db, vehicle_model, version)

    def create(self, db: Session, part_data: Dict[str, Any]):
        return self.repository.create(db, part_data)

    def bulk_create(self, db: Session, parts_data: List[Dict[str, Any]]):
        return self.repository.bulk_create(db, parts_data)

    def update(self, db: Session, part_id: int, update_data: Dict[str, Any]):
        return self.repository.update(db, part_id, update_data)

    def delete_by_vehicle_version(self, db: Session, vehicle_model: str, version: str) -> int:
        return self.repository.delete_by_vehicle_version(db, vehicle_model, version)
