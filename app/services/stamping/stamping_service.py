"""
冲压工艺 Service
业务逻辑层，处理业务规则和事务
"""

import logging
from typing import Any, List, Dict

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.dto.stamping_part_dto import StampingPartBatchDeleteDTO
from app.schemas.vo.stamping_vo import (
    StampingPartQuery,
    StampingPartListResponse,
    StampingPartWithProcessesResponse,
    StampingProcessResponse,
    StampingPartListFilterOptions,
    StampingCascadeFilterOptionsVO,
    StampingCascadeFilterQuery,
    StampingPartBatchDeleteResultVO,
)
from app.exceptions import BusinessException, NotFoundException
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.stamping")


class StampingPartService:
    """零件业务逻辑"""

    def __init__(self) -> None:
        self.repository = StampingPartRepository()
        self.process_repository = StampingProcessRepository()

    def count_parts(self, db: Session) -> int:
        """零件总数。"""
        return self.repository.count_all(db)

    def count_processes(self, db: Session) -> int:
        """工序总数。"""
        return self.process_repository.count_all(db)

    def count_vehicle_models(self, db: Session) -> int:
        """去重车型数量。"""
        return self.repository.count_distinct_vehicle_models(db)

    def list_parts(
        self, db: Session, query: StampingPartQuery
    ) -> tuple[List[StampingPartListResponse], int, StampingPartListFilterOptions]:
        """获取零件列表（不含工序详情，含工序统计数 process_count）"""
        skip = (query.page - 1) * query.size
        location = query.location
        vehicle_model = query.vehicle_model
        version = query.version
        part_number = query.part_number
        part_name = query.part_name
        stamping_supplier = query.stamping_supplier
        parts, total = self.repository.paginate(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            stamping_supplier=stamping_supplier,
            skip=skip,
            limit=query.size,
        )
        # 一次聚合查询补齐每行工序数（避免 ORM lazy load 触发 N+1）
        part_ids = [p.id for p in parts]
        process_counts = self.repository.count_processes_by_part_ids(db, part_ids)

        rows = []
        for p in parts:
            row = StampingPartListResponse.model_validate(p)
            row.process_count = process_counts.get(p.id, 0)
            rows.append(row)

        # 筛选下拉框选项 + 当前筛选下去重维度汇总
        filter_options: dict[str, Any] = self.repository.get_filter_options(db)
        filter_options["summary"] = self.repository.summarize_by_filters(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            stamping_supplier=stamping_supplier,
        )
        filter_vo = StampingPartListFilterOptions.model_validate(filter_options)
        return rows, total, filter_vo

    def get_filter_options(self, db: Session) -> StampingPartListFilterOptions:
        """获取筛选下拉框的可选值"""
        raw = self.repository.get_filter_options(db)
        return StampingPartListFilterOptions.model_validate(raw)

    def get_cascade_filter_options(
        self,
        db: Session,
        query: StampingCascadeFilterQuery,
    ) -> StampingCascadeFilterOptionsVO:
        """获取基地 → 冲压工厂 → 配套车型 级联筛选选项"""
        raw = self.repository.get_cascade_filter_options(
            db,
            location=query.location.strip() if query.location else None,
            stamping_supplier=query.stamping_supplier.strip() if query.stamping_supplier else None,
            vehicle_model=query.vehicle_model.strip() if query.vehicle_model else None,
        )
        return StampingCascadeFilterOptionsVO.model_validate(raw)

    def list_materials(
        self, db: Session, query: Any
    ) -> tuple[list[Any], int, StampingPartListFilterOptions]:
        """获取材料列表（去重 material + thickness + sheet_length + sheet_width）"""
        from app.schemas.vo.stamping_vo import StampingMaterialResponse

        skip = (query.page - 1) * query.size
        parts, total = self.repository.paginate_materials(
            db,
            location=query.location,
            stamping_supplier=query.stamping_supplier,
            vehicle_model=query.vehicle_model,
            version=query.version,
            skip=skip,
            limit=query.size,
        )

        rows = [StampingMaterialResponse.model_validate(p) for p in parts]
        filter_options = self.repository.get_filter_options(db)
        filter_vo = StampingPartListFilterOptions.model_validate(filter_options)
        return rows, total, filter_vo

    def count_material_specs(
        self,
        db: Session,
        *,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> int:
        """统计去重后的材料+厚度规格行数。"""
        return self.repository.count_material_specs(
            db,
            location=location.strip() if location else None,
            stamping_supplier=stamping_supplier.strip() if stamping_supplier else None,
            vehicle_model=vehicle_model.strip() if vehicle_model else None,
            version=version.strip() if version else None,
        )

    def list_material_specs(
        self,
        db: Session,
        *,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[dict[str, Any]]:
        """列出去重后的 基地 + 材料(钢种) + 厚度（钢价计算用）。"""
        return self.repository.list_material_specs(
            db,
            location=location.strip() if location else None,
            stamping_supplier=stamping_supplier.strip() if stamping_supplier else None,
            vehicle_model=vehicle_model.strip() if vehicle_model else None,
            version=version.strip() if version else None,
        )

    def get_by_id(self, db: Session, part_id: int) -> StampingPartWithProcessesResponse:
        """获取单个零件（含工序）"""
        part = self.repository.get_by_id(db, part_id)
        if not part:
            raise NotFoundException(f"零件不存在: id={part_id}")
        return StampingPartWithProcessesResponse.model_validate(part)

    def delete(self, db: Session, part_id: int) -> None:
        """删除零件（硬删除，不写审计字段）。"""
        self.repository.delete(db, part_id)

    def get_id_map(self, db: Session, vehicle_model: str, version: str) -> Dict[str, int]:
        """获取零件号映射"""
        return self.repository.get_id_map_by_vehicle_version(db, vehicle_model, version)

    def create(
        self,
        db: Session,
        part_data: Dict[str, Any],
        current_user: UserVO,
    ) -> Any:
        payload = {**part_data, **audit_create(current_user)}
        return self.repository.create(db, payload)

    def bulk_create(
        self,
        db: Session,
        parts_data: List[Dict[str, Any]],
        current_user: UserVO,
    ) -> Any:
        audit = audit_create(current_user)
        rows = [{**row, **audit} for row in parts_data]
        return self.repository.bulk_create(db, rows)

    def update(
        self,
        db: Session,
        part_id: int,
        update_data: Dict[str, Any],
        current_user: UserVO,
    ) -> Any:
        payload = {**update_data, **audit_update(current_user)}
        return self.repository.update(db, part_id, payload)

    def delete_by_vehicle_version(self, db: Session, vehicle_model: str, version: str) -> int:
        """按车型+版本硬删除零件（上传覆盖旧数据时使用）。"""
        return self.repository.delete_by_vehicle_version(db, vehicle_model, version)

    def batch_delete(
        self,
        db: Session,
        dto: StampingPartBatchDeleteDTO,
    ) -> StampingPartBatchDeleteResultVO:
        """按基地 + 冲压工厂 + 车型（版本可选）批量删除零件。"""
        location = dto.location.strip()
        supplier = dto.stamping_supplier.strip()
        vehicle_model = dto.vehicle_model.strip()
        version = dto.version.strip() if dto.version else None
        if not location or not supplier or not vehicle_model:
            raise BusinessException("基地、冲压工厂和车型不能为空")

        deleted = self.repository.delete_by_scope(
            db,
            location=location,
            stamping_supplier=supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        db.commit()
        return StampingPartBatchDeleteResultVO(
            location=location,
            stamping_supplier=supplier,
            vehicle_model=vehicle_model,
            version=version,
            deleted_count=deleted,
        )

    def update_process(
        self,
        db: Session,
        process_id: int,
        update_data: Dict[str, Any],
        current_user: UserVO,
    ) -> StampingProcessResponse:
        """更新单个工序"""
        from app.repositories.stamping.stamping_repository import StampingProcessRepository

        process_repo = StampingProcessRepository()
        payload = {**update_data, **audit_update(current_user)}
        process = process_repo.update(db, process_id, payload)
        if not process:
            raise NotFoundException(f"工序不存在: id={process_id}")
        return StampingProcessResponse.model_validate(process)

    def batch_update_processes(
        self,
        db: Session,
        items: List[Dict[str, Any]],
        current_user: UserVO,
    ) -> int:
        """批量更新工序成本系数"""
        from app.repositories.stamping.stamping_repository import StampingProcessRepository

        audit = audit_update(current_user)
        process_repo = StampingProcessRepository()
        count = 0
        for item in items:
            pid = item.get("id")
            if not pid:
                continue
            update_data = {k: v for k, v in item.items() if k != "id"}
            if not update_data:
                logger.warning("process_id=%s 的 update_data 为空，跳过", pid)
                continue
            update_data.update(audit)
            if process_repo.update(db, int(pid), update_data):
                count += 1
        logger.info("batch_update_processes 完成，更新了 %s 条", count)
        return count
