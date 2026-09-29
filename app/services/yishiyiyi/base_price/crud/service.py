"""钢材基准价格 CRUD 服务。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.period import previous_month
from app.exceptions.base import BusinessException, NotFoundException
from app.models.yishiyiyi import SteelBasePrice
from app.repositories.yishiyiyi.base_price.steel_base_price_repository import (
    BasePriceFilter,
    SteelBasePriceRepository,
)
from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.schemas.vo.steel_base_price_vo import (
    SteelBasePriceFilterOptionsVO,
    SteelBasePriceResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.steel_grade_category.service import (
    SteelGradeCategoryService,
)
from app.services.masterdata.steel_mill.service import SteelMillService
from app.services.settings.system.service import SettingsService
from app.services.yishiyiyi.base_price.gate import (
    AwardLine,
    reject_excessive_month_moves,
    reject_invalid_base_price_award,
    reject_processing_fee_over_limit,
)

logger = logging.getLogger("service.steel_base_price.crud")


def _mill_id(db: Session, raw: str | None) -> int | None:
    return SteelMillService().filter_id(db, raw)


def _with_abbreviation(
    db: Session,
    records: list[SteelBasePrice],
) -> list[SteelBasePriceResponse]:
    hits = SteelMillService().hits_by_id(db)
    rows: list[SteelBasePriceResponse] = []
    for record in records:
        vo = SteelBasePriceResponse.model_validate(record)
        hit = hits.get(record.steel_mill_id)
        if hit is not None:
            vo.steel_mill_abbreviation = hit.abbreviation
        rows.append(vo)
    return rows


def _reject_line_against_previous_month(
    db: Session,
    repository: SteelBasePriceRepository,
    line: AwardLine,
    *,
    year: int,
    month: int,
) -> None:
    prev_year, prev_month = previous_month(year, month)
    previous_rows = repository.list_by_year_month(db, year=prev_year, month=prev_month)
    previous = [
        AwardLine(
            location=row.location,
            steel_mill=row.steel_mill,
            grade=row.grade,
            thick=row.thick,
            width=row.width,
            base_price=row.base_price,
            processing_fee=row.processing_fee,
        )
        for row in previous_rows
    ]
    limit = SettingsService().get_base_price_month_move_limit(db)
    reject_excessive_month_moves([line], previous, limit=limit)


class SteelBasePriceCrudService:
    """钢材基准价格主表 CRUD 与查询统计。"""

    def __init__(self) -> None:
        self.repository = SteelBasePriceRepository()

    def get_filter_options(self, db: Session) -> SteelBasePriceFilterOptionsVO:
        options = self.repository.get_filter_options(db)
        return SteelBasePriceFilterOptionsVO.model_validate(
            {
                **options,
                "locations": LocationService().list_registered(db),
                "steel_mills": [item.abbreviation for item in SteelMillService().list_enabled(db)],
            }
        )

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
            steel_mill_id=_mill_id(db, query.steel_mill),
            category_name=query.category_name.strip() if query.category_name else None,
            grade=query.grade.strip() if query.grade else None,
            spec=query.spec.strip() if query.spec else None,
            skip=skip,
            limit=query.size,
        )
        records, total = self.repository.paginate(db, base_filter)
        return _with_abbreviation(db, records), total

    def get_by_id(self, db: Session, record_id: int) -> SteelBasePriceResponse:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("记录不存在")
        rows = _with_abbreviation(db, [record])
        return rows[0]

    def create(
        self,
        db: Session,
        body: SteelBasePriceCreate,
        current_user: UserVO,
    ) -> SteelBasePriceResponse:
        try:
            canonical = LocationService().require_enabled(db, body.location)
            mill = SteelMillService().require_enabled(db, body.steel_mill)
            archive = SteelGradeCategoryService().require_matched_grade(db, body.grade)
            if archive is None:
                raise BusinessException("牌号不能为空")
            body = body.model_copy(
                update={
                    "location": canonical,
                    "grade": archive.grade,
                    "category_name": archive.category_name,
                }
            )
            stored = self.repository.list_by_year_month(db, year=body.year, month=body.month)
            incoming = [
                AwardLine(
                    location=body.location,
                    grade=body.grade,
                    steel_mill=body.steel_mill,
                    thick=body.thick,
                    width=body.width,
                    processing_fee=body.processing_fee,
                    base_price=body.base_price,
                    excel_row=body.excel_row,
                )
            ]
            reject_invalid_base_price_award(
                incoming,
                [
                    AwardLine(
                        location=row.location,
                        grade=row.grade,
                        steel_mill=row.steel_mill,
                        thick=row.thick,
                        width=row.width,
                    )
                    for row in stored
                ],
                max_thickness=SettingsService().get_body_panel_max_thickness(db),
            )
            reject_processing_fee_over_limit(
                incoming,
                limit=SettingsService().get_base_price_processing_fee_limit(db),
            )
            _reject_line_against_previous_month(
                db,
                self.repository,
                incoming[0],
                year=body.year,
                month=body.month,
            )
            audit = audit_create(current_user)
            record = self.repository.create(
                db,
                body,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
            record.steel_mill_id = mill.id
            record.canonical_steel_mill = mill.full_name
            db.commit()
            return _with_abbreviation(db, [record])[0]
        except IntegrityError:
            db.rollback()
            raise BusinessException("基准价格已存在，或牌号不在「主数据 → 牌号分类」") from None
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
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
        price_fields = body.model_fields_set & {"base_price", "processing_fee"}
        try:
            existing = self.repository.get_by_id(db, record_id)
            if existing is None:
                raise NotFoundException("记录不存在")
            if price_fields:
                line = AwardLine(
                    location=existing.location,
                    grade=existing.grade,
                    steel_mill=existing.steel_mill,
                    thick=existing.thick,
                    width=existing.width,
                    base_price=body.base_price
                    if body.base_price is not None
                    else existing.base_price,
                    processing_fee=body.processing_fee
                    if body.processing_fee is not None
                    else existing.processing_fee,
                )
                if body.processing_fee is not None:
                    reject_processing_fee_over_limit(
                        [line],
                        limit=SettingsService().get_base_price_processing_fee_limit(db),
                    )
                _reject_line_against_previous_month(
                    db,
                    self.repository,
                    line,
                    year=existing.year,
                    month=existing.month,
                )
            record = self.repository.update(
                db,
                record_id,
                body,
                updated_by=display_name(current_user),
            )
            if record is None:
                raise NotFoundException("记录不存在")
            db.commit()
            rows = _with_abbreviation(db, [record])
            return rows[0]
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
                steel_mill_id=_mill_id(db, steel_mill),
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
            steel_mill_id=_mill_id(db, steel_mill),
            spec=spec.strip() if spec else None,
            grades_in=grades_in,
        )
