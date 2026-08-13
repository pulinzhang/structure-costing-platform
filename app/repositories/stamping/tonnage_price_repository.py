"""
冲次单价 Repository
数据访问层，只负责与数据库交互
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.stamping_tonnage_price import StampingTonnagePrice


logger = logging.getLogger("repository.stamping")


class StampingTonnagePriceRepository:
    """冲次单价数据访问"""

    def get_by_id(self, db: Session, id: int) -> Optional[StampingTonnagePrice]:
        """根据 ID 查询单条记录"""
        return db.query(StampingTonnagePrice).filter(StampingTonnagePrice.id == id).first()

    def get_by_location_year_tonnage(
        self, db: Session, location: str, year: int, tonnage: int
    ) -> Optional[StampingTonnagePrice]:
        """根据基地、年份和吨位查询记录"""
        return (
            db.query(StampingTonnagePrice)
            .filter(
                and_(
                    StampingTonnagePrice.location == location,
                    StampingTonnagePrice.year == year,
                    StampingTonnagePrice.tonnage == tonnage,
                )
            )
            .first()
        )

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> List[StampingTonnagePrice]:
        """查询指定基地+年份的所有记录"""
        return (
            db.query(StampingTonnagePrice)
            .filter(
                and_(
                    StampingTonnagePrice.location == location,
                    StampingTonnagePrice.year == year,
                )
            )
            .order_by(StampingTonnagePrice.tonnage)
            .all()
        )

    def list_by_year(self, db: Session, year: int) -> List[StampingTonnagePrice]:
        """查询指定年份的所有记录（跨基地）"""
        return (
            db.query(StampingTonnagePrice)
            .filter(StampingTonnagePrice.year == year)
            .order_by(StampingTonnagePrice.location, StampingTonnagePrice.tonnage)
            .all()
        )

    def paginate(
        self,
        db: Session,
        location: Optional[str] = None,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StampingTonnagePrice], int]:
        """分页查询"""
        q = db.query(StampingTonnagePrice)
        if location is not None:
            q = q.filter(StampingTonnagePrice.location == location)
        if year is not None:
            q = q.filter(StampingTonnagePrice.year == year)

        total = q.count()
        records = (
            q.order_by(
                StampingTonnagePrice.location,
                StampingTonnagePrice.year,
                StampingTonnagePrice.tonnage,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def list_for_export(
        self,
        db: Session,
        location: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[StampingTonnagePrice]:
        """按筛选条件导出全量记录（不分页）"""
        q = db.query(StampingTonnagePrice)
        if location is not None:
            q = q.filter(StampingTonnagePrice.location == location)
        if year is not None:
            q = q.filter(StampingTonnagePrice.year == year)
        return (
            q.order_by(
                StampingTonnagePrice.location,
                StampingTonnagePrice.year,
                StampingTonnagePrice.tonnage,
            )
            .all()
        )

    def list_all(self, db: Session) -> List[StampingTonnagePrice]:
        """查询所有记录"""
        return (
            db.query(StampingTonnagePrice)
            .order_by(
                StampingTonnagePrice.location,
                StampingTonnagePrice.year,
                StampingTonnagePrice.tonnage,
            )
            .all()
        )

    def get_distinct_locations(self, db: Session) -> List[str]:
        """获取所有基地列表"""
        results = (
            db.query(StampingTonnagePrice.location)
            .distinct()
            .order_by(StampingTonnagePrice.location)
            .all()
        )
        return [r[0] for r in results]

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

    def create(
        self, db: Session, data: Dict[str, Any], *, commit: bool = True
    ) -> StampingTonnagePrice:
        """创建单条记录"""
        record = StampingTonnagePrice(**data)
        db.add(record)
        if commit:
            db.commit()
        else:
            db.flush()
        db.refresh(record)
        logger.info(
            "创建冲次单价: location=%s, year=%s, tonnage=%s, id=%s",
            data.get("location"),
            data.get("year"),
            data.get("tonnage"),
            record.id,
        )
        return record

    def bulk_create(self, db: Session, data_list: List[Dict[str, Any]]) -> List[StampingTonnagePrice]:
        """批量创建记录"""
        records = [StampingTonnagePrice(**data) for data in data_list]
        db.add_all(records)
        db.commit()
        for record in records:
            db.refresh(record)
        logger.info("批量创建冲次单价: %s 条", len(records))
        return records

    def update(
        self,
        db: Session,
        id: int,
        update_data: Dict[str, Any],
        *,
        commit: bool = True,
    ) -> Optional[StampingTonnagePrice]:
        """更新记录"""
        record = self.get_by_id(db, id)
        if not record:
            return None
        for key, value in update_data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        if commit:
            db.commit()
        else:
            db.flush()
        db.refresh(record)
        logger.info("更新冲次单价: id=%s", id)
        return record

    def delete(self, db: Session, id: int) -> bool:
        """删除记录"""
        record = self.get_by_id(db, id)
        if not record:
            return False
        db.delete(record)
        db.commit()
        logger.info("删除冲次单价: id=%s", id)
        return True

    def delete_by_location_year(self, db: Session, location: str, year: int) -> int:
        """删除指定基地+年份的所有记录"""
        count = (
            db.query(StampingTonnagePrice)
            .filter(
                and_(
                    StampingTonnagePrice.location == location,
                    StampingTonnagePrice.year == year,
                )
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("删除基地 %s 年份 %s 的冲次单价: %s 条", location, year, count)
        return count
