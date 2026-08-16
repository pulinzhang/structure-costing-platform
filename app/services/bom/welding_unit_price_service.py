"""
焊接工费单价 Service
业务逻辑层，处理业务规则和事务
"""

import logging
from typing import Any, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.repositories.bom.welding_unit_price_repository import BomWeldingUnitPriceRepository
from app.schemas.dto.bom_welding_unit_price_dto import (
    BomWeldingUnitPriceCreate,
    BomWeldingUnitPriceQuery,
    BomWeldingUnitPriceUpdate,
)
from app.schemas.vo.bom_welding_unit_price_vo import BomWeldingUnitPriceResponse
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.bom")


class BomWeldingUnitPriceService:
    """焊接工费单价业务逻辑"""

    def __init__(self) -> None:
        self.repository = BomWeldingUnitPriceRepository()

    def list_by_year(self, db: Session, year: int) -> List[BomWeldingUnitPriceResponse]:
        records = self.repository.list_by_year(db, year)
        return [BomWeldingUnitPriceResponse.model_validate(r) for r in records]

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> List[BomWeldingUnitPriceResponse]:
        records = self.repository.list_by_location_year(db, location, year)
        return [BomWeldingUnitPriceResponse.model_validate(r) for r in records]

    def list_all(self, db: Session) -> List[BomWeldingUnitPriceResponse]:
        records = self.repository.list_all(db)
        return [BomWeldingUnitPriceResponse.model_validate(r) for r in records]

    def paginate(
        self, db: Session, query: BomWeldingUnitPriceQuery
    ) -> Tuple[List[BomWeldingUnitPriceResponse], int, dict[str, Any]]:
        skip = (query.page - 1) * query.size
        records, total = self.repository.paginate(
            db,
            location=query.location,
            year=query.year,
            skip=skip,
            limit=query.size,
        )
        rows = [BomWeldingUnitPriceResponse.model_validate(r) for r in records]
        filters = {
            "locations": self.repository.get_distinct_locations(db),
            "years": self.repository.get_distinct_years(db),
        }
        return rows, total, filters

    def get_by_id(self, db: Session, id: int) -> Optional[BomWeldingUnitPriceResponse]:
        record = self.repository.get_by_id(db, id)
        if not record:
            return None
        return BomWeldingUnitPriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: BomWeldingUnitPriceCreate,
        current_user: UserVO,
    ) -> Tuple[Optional[BomWeldingUnitPriceResponse], Optional[str]]:
        try:
            payload = {**data.model_dump(), **audit_create(current_user)}
            record = self.repository.create(db, payload)
            return BomWeldingUnitPriceResponse.model_validate(record), None
        except IntegrityError:
            db.rollback()
            error_msg = (
                f"该基地({data.location})、年份({data.year})"
                f"和项目「{data.item_name}」的记录已存在"
            )
            logger.warning(error_msg)
            return None, error_msg
        except Exception as e:
            db.rollback()
            logger.error("创建焊接工费单价失败: %s", e)
            return None, str(e)

    def bulk_upsert(
        self,
        db: Session,
        items: List[BomWeldingUnitPriceCreate],
        current_user: UserVO,
    ) -> Tuple[
        List[BomWeldingUnitPriceResponse],
        List[BomWeldingUnitPriceResponse],
        List[str],
    ]:
        created: List[BomWeldingUnitPriceResponse] = []
        updated: List[BomWeldingUnitPriceResponse] = []
        failed: List[str] = []

        for item in items:
            existing = self.repository.get_by_location_year_item(
                db, item.location, item.year, item.item_name
            )
            if existing:
                record, error = self.update(
                    db,
                    existing.id,
                    BomWeldingUnitPriceUpdate(
                        unit=item.unit,
                        unit_price=item.unit_price,
                        remark=item.remark,
                    ),
                    current_user=current_user,
                )
                if record:
                    updated.append(record)
                else:
                    failed.append(
                        error
                        or f"{item.location}/{item.year}/{item.item_name} 更新失败"
                    )
                continue

            record, error = self.create(db, item, current_user=current_user)
            if record:
                created.append(record)
            else:
                failed.append(error or "未知错误")

        return created, updated, failed

    def update(
        self,
        db: Session,
        id: int,
        data: BomWeldingUnitPriceUpdate,
        current_user: UserVO,
    ) -> Tuple[Optional[BomWeldingUnitPriceResponse], Optional[str]]:
        try:
            payload = {
                **data.model_dump(exclude_unset=True),
                **audit_update(current_user),
            }
            record = self.repository.update(db, id, payload)
            if not record:
                return None, "记录不存在"
            return BomWeldingUnitPriceResponse.model_validate(record), None
        except Exception as e:
            db.rollback()
            logger.error("更新焊接工费单价失败: %s", e)
            return None, str(e)

    def delete(self, db: Session, id: int) -> Tuple[bool, Optional[str]]:
        success = self.repository.delete(db, id)
        if not success:
            return False, "记录不存在"
        return True, None

    def batch_delete_by_location_year(
        self,
        db: Session,
        *,
        location: str,
        year: int,
    ) -> Tuple[int, Optional[str]]:
        location = (location or "").strip()
        if not location:
            return 0, "请选择采购基地"
        if year < 2000 or year > 2100:
            return 0, "请选择正确的年度"

        existing = self.repository.list_by_location_year(db, location, year)
        if not existing:
            return 0, f"基地「{location}」{year} 年没有可删除的数据"

        deleted_count = self.repository.delete_by_location_year(db, location, year)
        logger.info(
            "批量删除焊接工费单价: location=%s year=%s count=%s",
            location,
            year,
            deleted_count,
        )
        return deleted_count, None

    def copy_from_year(
        self,
        db: Session,
        location: str,
        source_year: int,
        target_year: int,
        current_user: UserVO,
    ) -> Tuple[int, int, List[str]]:
        audit = audit_create(current_user)
        source_records = self.repository.list_by_location_year(db, location, source_year)
        if not source_records:
            return 0, 0, [f"基地「{location}」源年份 {source_year} 没有数据"]

        target_records = self.repository.list_by_location_year(db, location, target_year)
        if target_records:
            self.repository.delete_by_location_year(db, location, target_year)

        created = 0
        skipped = 0
        failed: List[str] = []

        for source in source_records:
            try:
                self.repository.create(
                    db,
                    {
                        "location": location,
                        "year": target_year,
                        "item_name": source.item_name,
                        "unit": source.unit,
                        "unit_price": source.unit_price,
                        "remark": source.remark,
                        **audit,
                    },
                )
                created += 1
            except IntegrityError:
                db.rollback()
                skipped += 1
            except Exception as e:
                db.rollback()
                failed.append(f"{source.item_name}: {str(e)}")

        logger.info(
            "基地 %s 从 %s 复制到 %s: 创建 %s, 跳过 %s, 失败 %s",
            location,
            source_year,
            target_year,
            created,
            skipped,
            len(failed),
        )
        return created, skipped, failed

    def get_locations(self, db: Session) -> List[str]:
        return self.repository.get_distinct_locations(db)

    def get_years(self, db: Session) -> List[int]:
        return self.repository.get_distinct_years(db)
