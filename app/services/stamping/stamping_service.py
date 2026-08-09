"""
冲压工艺 Service
业务逻辑层，处理业务规则和事务
"""

import logging
from typing import Dict, List

from sqlalchemy.orm import Session

from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.vo.stamping_vo import (
    StampingPartQuery,
    StampingPartListResponse,
    StampingPartWithProcessesResponse,
    StampingProcessResponse,
    StampingPartListFilterOptions,
)
from app.exceptions import NotFoundException

logger = logging.getLogger("service.stamping")


class StampingPartService:
    """零件业务逻辑"""

    def __init__(self):
        self.part_repo = StampingPartRepository()
        self.process_repo = StampingProcessRepository()

    def list_parts(
        self, db: Session, query: StampingPartQuery
    ) -> tuple[List[StampingPartListResponse], int, StampingPartListFilterOptions]:
        """获取零件列表（不含工序详情，含工序统计数 process_count）"""
        skip = (query.page - 1) * query.size
        parts, total = self.part_repo.paginate(
            db,
            location=query.location,
            vehicle_model=query.vehicle_model,
            version=query.version,
            part_number=query.part_number,
            part_name=query.part_name,
            stamping_supplier=query.stamping_supplier,
            skip=skip,
            limit=query.size,
        )
        # 一次聚合查询补齐每行工序数（避免 ORM lazy load 触发 N+1）
        part_ids = [p.id for p in parts]
        process_counts = self.part_repo.count_processes_by_part_ids(db, part_ids)

        rows = []
        for p in parts:
            row = StampingPartListResponse.model_validate(p)
            row.process_count = process_counts.get(p.id, 0)
            rows.append(row)

        # 筛选下拉框选项
        filter_options = self.part_repo.get_filter_options(db)
        filter_vo = StampingPartListFilterOptions.model_validate(filter_options)
        return rows, total, filter_vo

    def get_by_id(self, db: Session, part_id: int) -> StampingPartWithProcessesResponse:
        """获取单个零件（含工序）"""
        part = self.part_repo.get_by_id(db, part_id)
        if not part:
            raise NotFoundException(f"零件不存在: id={part_id}")
        return StampingPartWithProcessesResponse.model_validate(part)

    def delete(self, db: Session, part_id: int) -> None:
        """删除零件"""
        self.part_repo.delete(db, part_id)
        db.commit()

    def update_process(
        self,
        db: Session,
        process_id: int,
        update_data: Dict[str, any],
    ) -> StampingProcessResponse:
        """更新单个工序"""
        process = self.process_repo.update(db, process_id, update_data)
        if not process:
            raise NotFoundException(f"工序不存在: id={process_id}")
        db.commit()
        return StampingProcessResponse.model_validate(process)

    def batch_update_processes(self, db: Session, items: List[Dict[str, any]]) -> int:
        """批量更新工序成本系数"""
        count = 0
        for item in items:
            pid = item.get("id")
            if not pid:
                continue
            update_data = {k: v for k, v in item.items() if k != "id"}
            if not update_data:
                logger.warning("process_id=%s 的 update_data 为空，跳过", pid)
                continue
            if self.process_repo.update(db, int(pid), update_data):
                count += 1
        db.commit()
        logger.info("batch_update_processes 完成，更新了 %s 条", count)
        return count
