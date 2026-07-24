"""
吨位价格 Repository
数据访问层，只负责与数据库交互
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import StampingTonnagePrice


logger = logging.getLogger("repository.stamping")


class StampingTonnagePriceRepository:
    """吨位价格数据访问"""

    def get_by_id(self, db: Session, id: int) -> Optional[StampingTonnagePrice]:
        """根据 ID 查询单条记录"""
        return db.query(StampingTonnagePrice).filter(StampingTonnagePrice.id == id).first()

    def get_by_year_tonnage(
        self, db: Session, year: int, tonnage: int
    ) -> Optional[StampingTonnagePrice]:
        """根据年份和吨位查询记录"""
        return (
            db.query(StampingTonnagePrice)
            .filter(
                and_(
                    StampingTonnagePrice.year == year,
                    StampingTonnagePrice.tonnage == tonnage,
                )
            )
            .first()
        )

    def list_by_year(self, db: Session, year: int) -> List[StampingTonnagePrice]:
        """查询指定年份的所有记录"""
        return (
            db.query(StampingTonnagePrice)
            .filter(StampingTonnagePrice.year == year)
            .order_by(StampingTonnagePrice.tonnage)
            .all()
        )

    def paginate(
        self,
        db: Session,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StampingTonnagePrice], int]:
        """分页查询"""
        q = db.query(StampingTonnagePrice)
        if year is not None:
            q = q.filter(StampingTonnagePrice.year == year)

        total = q.count()
        records = (
            q.order_by(StampingTonnagePrice.year, StampingTonnagePrice.tonnage)
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def list_all(self, db: Session) -> List[StampingTonnagePrice]:
        """查询所有记录"""
        return (
            db.query(StampingTonnagePrice)
            .order_by(StampingTonnagePrice.year, StampingTonnagePrice.tonnage)
            .all()
        )

    def get_distinct_years(self, db: Session) -> List[int]:
        """获取所有年份列表"""
        results = (
            db.query(StampingTonnagePrice.year)
            .distinct()
            .order_by(StampingTonnagePrice.year.desc())
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_tonnages(self, db: Session) -> List[int]:
        """获取所有吨位列表"""
        results = (
            db.query(StampingTonnagePrice.tonnage)
            .distinct()
            .order_by(StampingTonnagePrice.tonnage)
            .all()
        )
        return [r[0] for r in results]

    def create(self, db: Session, data: Dict[str, Any]) -> StampingTonnagePrice:
        """创建单条记录"""
        record = StampingTonnagePrice(**data)
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"创建吨位价格: year={data.get('year')}, tonnage={data.get('tonnage')}, id={record.id}")
        return record

    def bulk_create(self, db: Session, data_list: List[Dict[str, Any]]) -> List[StampingTonnagePrice]:
        """批量创建记录"""
        records = [StampingTonnagePrice(**data) for data in data_list]
        db.add_all(records)
        db.commit()
        for record in records:
            db.refresh(record)
        logger.info(f"批量创建吨位价格: {len(records)} 条")
        return records

    def update(
        self, db: Session, id: int, update_data: Dict[str, Any]
    ) -> Optional[StampingTonnagePrice]:
        """更新记录"""
        record = self.get_by_id(db, id)
        if not record:
            return None
        for key, value in update_data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        db.commit()
        db.refresh(record)
        logger.info(f"更新吨位价格: id={id}")
        return record

    def delete(self, db: Session, id: int) -> bool:
        """删除记录"""
        record = self.get_by_id(db, id)
        if not record:
            return False
        db.delete(record)
        db.commit()
        logger.info(f"删除吨位价格: id={id}")
        return True

    def delete_by_year(self, db: Session, year: int) -> int:
        """删除指定年份的所有记录"""
        count = (
            db.query(StampingTonnagePrice)
            .filter(StampingTonnagePrice.year == year)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"删除年份 {year} 的吨位价格: {count} 条")
        return count
