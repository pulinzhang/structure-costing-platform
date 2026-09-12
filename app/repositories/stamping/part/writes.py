"""冲压零件写入与按范围删除。删除工序/拼焊子片与主表同一次 flush。"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.stamping import StampingPart, StampingProcess, StampingTailorWeldBlank
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.repositories.stamping.part.queries import StampingPartQueries
from app.schemas.dto.stamping_upload_dto import PartData, StampingPartPatch

logger = logging.getLogger("repository.stamping.part")


class StampingPartWrites:
    def __init__(self, queries: StampingPartQueries | None = None) -> None:
        self._queries = queries or StampingPartQueries()

    def create(self, db: Session, part_data: PartData) -> StampingPart:
        part = model_from_payload(StampingPart, part_data)
        db.add(part)
        db.flush()
        db.refresh(part)
        logger.info("创建零件: %s (id=%s)", part.part_number, part.id)
        return part

    def bulk_create(self, db: Session, parts_data: list[PartData]) -> list[StampingPart]:
        parts = [model_from_payload(StampingPart, data) for data in parts_data]
        db.add_all(parts)
        logger.info("批量创建零件: %s 个", len(parts))
        return parts

    def update(
        self, db: Session, part_id: int, update_data: StampingPartPatch
    ) -> StampingPart | None:
        part = self._queries.get_by_id(db, part_id)
        if not part:
            return None
        apply_payload_fields(
            part,
            update_data,
            skip=frozenset({"id", "created_by", "created_at"}),
        )
        db.flush()
        db.refresh(part)
        logger.info("更新零件: id=%s", part_id)
        return part

    def delete(self, db: Session, part_id: int) -> bool:
        """删除零件（关联工序由调用方处理，或依赖数据库外键级联删除）"""
        part = self._queries.get_by_id(db, part_id)
        if not part:
            return False
        db.delete(part)
        db.flush()
        logger.info(f"删除零件: id={part_id}")
        return True

    def delete_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        version: str,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
    ) -> int:
        """按基地 + 车型 + 版本批量删除零件及工序；工厂可选。不提交事务。

        使用 bulk DELETE + flush，确保旧行在后续 INSERT 前已从库中消失，
        避免唯一键 (location, supplier, model, version, part_number) 冲突。
        """
        parts = self._queries.get_all_by_scope(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
        )
        count = len(parts)
        if not parts:
            return 0

        part_ids = [part.id for part in parts]
        db.query(StampingProcess).filter(StampingProcess.part_id.in_(part_ids)).delete(
            synchronize_session=False
        )
        db.query(StampingTailorWeldBlank).filter(
            StampingTailorWeldBlank.part_id.in_(part_ids)
        ).delete(synchronize_session=False)
        db.query(StampingPart).filter(StampingPart.id.in_(part_ids)).delete(
            synchronize_session=False
        )
        db.flush()
        logger.info(
            "批量删除零件: %s/%s/%s/%s, 共 %s 个",
            location,
            stamping_supplier,
            vehicle_model,
            version,
            count,
        )
        return count

    def get_id_map_by_scope(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
    ) -> dict[str, int]:
        """获取范围内零件号到 ID 的映射。"""
        parts = self._queries.get_all_by_scope(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        return {p.part_number: p.id for p in parts if p.part_number}
