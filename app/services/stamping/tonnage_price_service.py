"""
冲次费率 Service
业务逻辑层，处理业务规则和事务
"""

import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.schemas.vo.stamping_tonnage_price_vo import StampingTonnagePriceResponse
from app.schemas.dto.stamping_tonnage_price_dto import (
    StampingTonnagePriceCreate,
    StampingTonnagePriceUpdate,
    StampingTonnagePriceQuery,
)


logger = logging.getLogger("service.stamping")


class StampingTonnagePriceService:
    """冲次费率业务逻辑"""

    def __init__(self):
        self.repository = StampingTonnagePriceRepository()

    def list_by_year(
        self, db: Session, year: int
    ) -> List[StampingTonnagePriceResponse]:
        """获取指定年份的所有冲次费率"""
        records = self.repository.list_by_year(db, year)
        return [StampingTonnagePriceResponse.model_validate(r) for r in records]

    def list_all(self, db: Session) -> List[StampingTonnagePriceResponse]:
        """获取所有冲次费率（按年份、吨位排序）"""
        records = self.repository.list_all(db)
        return [StampingTonnagePriceResponse.model_validate(r) for r in records]

    def paginate(
        self, db: Session, query: StampingTonnagePriceQuery
    ) -> Tuple[List[StampingTonnagePriceResponse], int, dict]:
        """分页查询冲次费率"""
        skip = (query.page - 1) * query.size
        records, total = self.repository.paginate(
            db,
            year=query.year,
            skip=skip,
            limit=query.size,
        )
        rows = [StampingTonnagePriceResponse.model_validate(r) for r in records]

        years = self.repository.get_distinct_years(db)
        tonnages = self.repository.get_distinct_tonnages(db)
        filters = {"years": years, "tonnages": tonnages}
        return rows, total, filters

    def get_by_id(self, db: Session, id: int) -> Optional[StampingTonnagePriceResponse]:
        """获取单个记录"""
        record = self.repository.get_by_id(db, id)
        if not record:
            return None
        return StampingTonnagePriceResponse.model_validate(record)

    def create(
        self, db: Session, data: StampingTonnagePriceCreate
    ) -> Tuple[Optional[StampingTonnagePriceResponse], Optional[str]]:
        """创建冲次费率记录，返回 (记录, 错误信息)"""
        try:
            record = self.repository.create(db, data.model_dump())
            return StampingTonnagePriceResponse.model_validate(record), None
        except IntegrityError:
            db.rollback()
            error_msg = f"该年份({data.year})和吨位({data.tonnage})的记录已存在"
            logger.warning(error_msg)
            return None, error_msg
        except Exception as e:
            db.rollback()
            logger.error(f"创建冲次费率失败: {e}")
            return None, str(e)

    def bulk_create(
        self, db: Session, items: List[StampingTonnagePriceCreate]
    ) -> Tuple[List[StampingTonnagePriceResponse], List[StampingTonnagePriceResponse], List[str]]:
        """
        批量创建冲次费率记录。
        返回 (成功列表, 跳过列表, 失败错误信息列表)。
        注意：跳过的记录不含详情数据，仅记录错误原因。
        """
        created: List[StampingTonnagePriceResponse] = []
        skipped: List[StampingTonnagePriceResponse] = []
        failed: List[str] = []

        for item in items:
            record, error = self.create(db, item)
            if record:
                created.append(record)
            elif error and "已存在" in error:
                skipped.append(
                    StampingTonnagePriceResponse(
                        id=0,
                        year=item.year,
                        tonnage=item.tonnage,
                        price_per_stroke=0.0,
                    )
                )
            else:
                failed.append(error or "未知错误")

        return created, skipped, failed

    def update(
        self, db: Session, id: int, data: StampingTonnagePriceUpdate
    ) -> Tuple[Optional[StampingTonnagePriceResponse], Optional[str]]:
        """更新冲次费率记录，返回 (记录, 错误信息)"""
        try:
            record = self.repository.update(db, id, data.model_dump())
            if not record:
                return None, "记录不存在"
            return StampingTonnagePriceResponse.model_validate(record), None
        except Exception as e:
            db.rollback()
            logger.error(f"更新冲次费率失败: {e}")
            return None, str(e)

    def delete(self, db: Session, id: int) -> Tuple[bool, Optional[str]]:
        """删除冲次费率记录，返回 (是否成功, 错误信息)"""
        success = self.repository.delete(db, id)
        if not success:
            return False, "记录不存在"
        return True, None

    def copy_from_year(
        self, db: Session, source_year: int, target_year: int
    ) -> Tuple[int, int, List[str]]:
        """
        从源年份复制价格到目标年份。
        返回 (创建数量, 跳过数量, 失败错误信息列表)。
        """
        source_records = self.repository.list_by_year(db, source_year)
        if not source_records:
            return 0, 0, [f"源年份 {source_year} 没有数据"]

        target_records = self.repository.list_by_year(db, target_year)
        if target_records:
            self.repository.delete_by_year(db, target_year)

        created = 0
        skipped = 0
        failed: List[str] = []

        for source in source_records:
            try:
                self.repository.create(db, {
                    "year": target_year,
                    "tonnage": source.tonnage,
                    "price_per_stroke": source.price_per_stroke,
                })
                created += 1
            except IntegrityError:
                db.rollback()
                skipped += 1
            except Exception as e:
                db.rollback()
                failed.append(f"吨位 {source.tonnage}: {str(e)}")

        logger.info(
            f"从 {source_year} 复制到 {target_year}: "
            f"创建 {created}, 跳过 {skipped}, 失败 {len(failed)}"
        )
        return created, skipped, failed

    def get_years(self, db: Session) -> List[int]:
        """获取所有年份列表"""
        return self.repository.get_distinct_years(db)

    def get_tonnages(self, db: Session) -> List[int]:
        """获取所有吨位列表"""
        return self.repository.get_distinct_tonnages(db)
