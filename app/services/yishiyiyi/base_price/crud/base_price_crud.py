"""钢材基准价格 CRUD 服务。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.exceptions.base import BusinessException, NotFoundException
from app.models.yishiyiyi import SteelBasePrice
from app.repositories.yishiyiyi.base_price import SteelBasePriceRepository
from app.repositories.yishiyiyi.base_price.steel_base_price_repository import (
    BasePriceFilter,
)
from app.schemas.dto.steel_base_price_dto import (
    FilterOptions,
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.schemas.vo.steel_base_price_vo import SteelBasePriceResponse
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.location.location_service import LocationService

logger = logging.getLogger("service.steel_base_price.crud")


class SteelBasePriceCrudService:
    """钢材基准价格主表 CRUD 与查询统计。"""

    def __init__(self) -> None:
        self.repository = SteelBasePriceRepository()

    def get_filter_options(self, db: Session) -> FilterOptions:
        options = self.repository.get_filter_options(db)
        return options.model_copy(update={"locations": LocationService().list_registered(db)})

    def paginate(
        self,
        db: Session,
        query: SteelBasePriceQuery,
    ) -> tuple[list[SteelBasePriceResponse], int]:
        skip = (query.page - 1) * query.size
        location_raw = query.location.strip() if query.location else None
        locations: list[str] | None = None
        if location_raw:
            locations = LocationService().expand_for_query(db, location_raw)
            if not locations:
                return [], 0
        base_filter = BasePriceFilter(
            year=query.year,
            month=query.month,
            locations=locations,
            steel_mill=query.steel_mill.strip() if query.steel_mill else None,
            category_name=query.category_name.strip() if query.category_name else None,
            grade=query.grade.strip() if query.grade else None,
            spec=query.spec.strip() if query.spec else None,
            skip=skip,
            limit=query.size,
        )
        records, total = self.repository.paginate(db, base_filter)
        return [SteelBasePriceResponse.model_validate(r) for r in records], total

    def get_by_id(self, db: Session, record_id: int) -> SteelBasePriceResponse:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("记录不存在")
        return SteelBasePriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        body: SteelBasePriceCreate,
        current_user: UserVO,
    ) -> SteelBasePriceResponse:
        try:
            canonical = LocationService().require_enabled(db, body.location)
            if canonical != body.location:
                body = body.model_copy(update={"location": canonical})
            audit = audit_create(current_user)
            record = self.repository.create(
                db,
                body,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
            db.commit()
            return SteelBasePriceResponse.model_validate(record)
        except Exception:
            db.rollback()
            logger.exception("创建基准价格失败")
            raise

    def update(
        self,
        db: Session,
        record_id: int,
        body: SteelBasePriceUpdate,
        current_user: UserVO,
    ) -> SteelBasePriceResponse:
        if not body.model_fields_set:
            raise BusinessException("没有提供任何更新字段")
        try:
            record = self.repository.update(
                db,
                record_id,
                body,
                updated_by=display_name(current_user),
            )
            if record is None:
                raise NotFoundException("记录不存在")
            db.commit()
            return SteelBasePriceResponse.model_validate(record)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新基准价格失败: id=%s", record_id)
            raise

    def delete(self, db: Session, record_id: int) -> None:
        try:
            success = self.repository.delete(db, record_id)
            if not success:
                raise NotFoundException("记录不存在")
            db.commit()
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除基准价格失败: id=%s", record_id)
            raise

    def batch_delete(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str | None = None,
        steel_mill: str | None = None,
    ) -> None:
        try:
            count = self.repository.delete_by_conditions(
                db,
                year=year,
                month=month,
                location=location,
                steel_mill=steel_mill,
            )
            db.commit()
            logger.info(
                "批量删除基准价格: year=%s month=%s location=%s steel_mill=%s count=%s",
                year,
                month,
                location,
                steel_mill,
                count,
            )
        except Exception:
            db.rollback()
            logger.exception("批量删除基准价格失败")
            raise

    def list_for_calc(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ) -> list[SteelBasePrice]:
        """钢价计算用：按年/月/基地取出全部基价 ORM（含 id 溯源）。"""
        return self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location.strip() if location else None,
        )

    def count_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        steel_mill: str | None = None,
        spec: str | None = None,
        grades_in: list[str] | None = None,
    ) -> int:
        return self.repository.count_for_export(
            db,
            year=year,
            month=month,
            location=location.strip() if location else None,
            steel_mill=steel_mill.strip() if steel_mill else None,
            spec=spec.strip() if spec else None,
            grades_in=grades_in,
        )
