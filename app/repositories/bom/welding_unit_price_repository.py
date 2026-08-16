"""
焊接工费单价 Repository
数据访问层，只负责与数据库交互
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.bom_welding_unit_price import BomWeldingUnitPrice

logger = logging.getLogger("repository.bom")


class BomWeldingUnitPriceRepository:
    """焊接工费单价数据访问"""

    def get_by_id(self, db: Session, id: int) -> Optional[BomWeldingUnitPrice]:
        return db.query(BomWeldingUnitPrice).filter(BomWeldingUnitPrice.id == id).first()

    def get_by_location_year_item(
        self, db: Session, location: str, year: int, item_name: str
    ) -> Optional[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .filter(
                and_(
                    BomWeldingUnitPrice.location == location,
                    BomWeldingUnitPrice.year == year,
                    BomWeldingUnitPrice.item_name == item_name,
                )
            )
            .first()
        )

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> List[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .filter(
                and_(
                    BomWeldingUnitPrice.location == location,
                    BomWeldingUnitPrice.year == year,
                )
            )
            .order_by(BomWeldingUnitPrice.item_name)
            .all()
        )

    def list_by_year(self, db: Session, year: int) -> List[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .filter(BomWeldingUnitPrice.year == year)
            .order_by(BomWeldingUnitPrice.location, BomWeldingUnitPrice.item_name)
            .all()
        )

    def paginate(
        self,
        db: Session,
        location: Optional[str] = None,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[BomWeldingUnitPrice], int]:
        q = db.query(BomWeldingUnitPrice)
        if location is not None:
            q = q.filter(BomWeldingUnitPrice.location == location)
        if year is not None:
            q = q.filter(BomWeldingUnitPrice.year == year)

        total = q.count()
        records = (
            q.order_by(
                BomWeldingUnitPrice.location,
                BomWeldingUnitPrice.year,
                BomWeldingUnitPrice.item_name,
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
    ) -> List[BomWeldingUnitPrice]:
        q = db.query(BomWeldingUnitPrice)
        if location is not None:
            q = q.filter(BomWeldingUnitPrice.location == location)
        if year is not None:
            q = q.filter(BomWeldingUnitPrice.year == year)
        return (
            q.order_by(
                BomWeldingUnitPrice.location,
                BomWeldingUnitPrice.year,
                BomWeldingUnitPrice.item_name,
            )
            .all()
        )

    def list_all(self, db: Session) -> List[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .order_by(
                BomWeldingUnitPrice.location,
                BomWeldingUnitPrice.year,
                BomWeldingUnitPrice.item_name,
            )
            .all()
        )

    def get_distinct_locations(self, db: Session) -> List[str]:
        results = (
            db.query(BomWeldingUnitPrice.location)
            .distinct()
            .order_by(BomWeldingUnitPrice.location)
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_years(self, db: Session) -> List[int]:
        results = (
            db.query(BomWeldingUnitPrice.year)
            .distinct()
            .order_by(BomWeldingUnitPrice.year.desc())
            .all()
        )
        return [r[0] for r in results]

    def create(
        self, db: Session, data: Dict[str, Any], *, commit: bool = True
    ) -> BomWeldingUnitPrice:
        record = BomWeldingUnitPrice(**data)
        db.add(record)
        if commit:
            db.commit()
        else:
            db.flush()
        db.refresh(record)
        logger.info(
            "创建焊接工费单价: location=%s, year=%s, item=%s, id=%s",
            data.get("location"),
            data.get("year"),
            data.get("item_name"),
            record.id,
        )
        return record

    def update(
        self,
        db: Session,
        id: int,
        update_data: Dict[str, Any],
        *,
        commit: bool = True,
    ) -> Optional[BomWeldingUnitPrice]:
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
        logger.info("更新焊接工费单价: id=%s", id)
        return record

    def delete(self, db: Session, id: int) -> bool:
        record = self.get_by_id(db, id)
        if not record:
            return False
        db.delete(record)
        db.commit()
        logger.info("删除焊接工费单价: id=%s", id)
        return True

    def delete_by_location_year(self, db: Session, location: str, year: int) -> int:
        count = (
            db.query(BomWeldingUnitPrice)
            .filter(
                and_(
                    BomWeldingUnitPrice.location == location,
                    BomWeldingUnitPrice.year == year,
                )
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("删除基地 %s 年份 %s 的焊接工费单价: %s 条", location, year, count)
        return count
