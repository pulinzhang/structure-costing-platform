"""
吨位价格 Service
业务逻辑层，处理业务规则和事务
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
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
    """吨位价格业务逻辑"""

    def __init__(self):
        self.repository = StampingTonnagePriceRepository()

    def list_by_year(
        self, db: Session, year: int
    ) -> List[Dict[str, Any]]:
        """获取指定年份的所有吨位价格"""
        records = self.repository.list_by_year(db, year)
        return [StampingTonnagePriceResponse.model_validate(r).model_dump() for r in records]

    def list_all(self, db: Session) -> List[Dict[str, Any]]:
        """获取所有吨位价格（按年份、吨位排序）"""
        records = self.repository.list_all(db)
        return [StampingTonnagePriceResponse.model_validate(r).model_dump() for r in records]

    def paginate(
        self, db: Session, query: StampingTonnagePriceQuery
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """分页查询吨位价格"""
        skip = (query.page - 1) * query.size
        records, total = self.repository.paginate(
            db,
            year=query.year,
            skip=skip,
            limit=query.size,
        )

        rows = [StampingTonnagePriceResponse.model_validate(r).model_dump() for r in records]

        # 获取下拉选项
        years = self.repository.get_distinct_years(db)
        tonnages = self.repository.get_distinct_tonnages(db)

        filters = {
            "years": years,
            "tonnages": tonnages,
        }

        return rows, total, filters

    def get_by_id(self, db: Session, id: int) -> Optional[Dict[str, Any]]:
        """获取单个记录"""
        record = self.repository.get_by_id(db, id)
        if not record:
            return None
        return StampingTonnagePriceResponse.model_validate(record).model_dump()

    def create(
        self, db: Session, data: StampingTonnagePriceCreate
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        创建吨位价格记录
        返回 (记录, 错误信息)
        """
        try:
            record = self.repository.create(db, data.model_dump())
            return StampingTonnagePriceResponse.model_validate(record).model_dump(), None
        except IntegrityError:
            db.rollback()
            error_msg = f"该年份({data.year})和吨位({data.tonnage})的记录已存在"
            logger.warning(error_msg)
            return None, error_msg
        except Exception as e:
            db.rollback()
            logger.error(f"创建吨位价格失败: {e}")
            return None, str(e)

    def bulk_create(
        self, db: Session, items: List[StampingTonnagePriceCreate]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        批量创建吨位价格记录
        返回 (成功列表, 跳过列表, 失败列表)
        """
        created = []
        skipped = []
        failed = []

        for item in items:
            record, error = self.create(db, item)
            if record:
                created.append(record)
            elif "已存在" in (error or ""):
                skipped.append({
                    "year": item.year,
                    "tonnage": item.tonnage,
                    "reason": error,
                })
            else:
                failed.append({
                    "year": item.year,
                    "tonnage": item.tonnage,
                    "reason": error,
                })

        return created, skipped, failed

    def update(
        self, db: Session, id: int, data: StampingTonnagePriceUpdate
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        更新吨位价格记录
        返回 (记录, 错误信息)
        """
        try:
            record = self.repository.update(db, id, data.model_dump())
            if not record:
                return None, "记录不存在"
            return StampingTonnagePriceResponse.model_validate(record).model_dump(), None
        except Exception as e:
            db.rollback()
            logger.error(f"更新吨位价格失败: {e}")
            return None, str(e)

    def delete(self, db: Session, id: int) -> Tuple[bool, Optional[str]]:
        """
        删除吨位价格记录
        返回 (是否成功, 错误信息)
        """
        success = self.repository.delete(db, id)
        if not success:
            return False, "记录不存在"
        return True, None

    def copy_from_year(
        self, db: Session, source_year: int, target_year: int
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        从源年份复制价格到目标年份
        返回 (创建数量, 跳过数量, 失败详情)
        """
        source_records = self.repository.list_by_year(db, source_year)
        if not source_records:
            return 0, 0, [{"reason": f"源年份 {source_year} 没有数据"}]

        # 检查目标年份是否已有数据
        target_records = self.repository.list_by_year(db, target_year)
        if target_records:
            # 删除旧数据
            self.repository.delete_by_year(db, target_year)

        created = 0
        skipped = 0
        failed = []

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
                failed.append({
                    "tonnage": source.tonnage,
                    "reason": str(e),
                })

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
