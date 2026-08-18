"""拼焊子片数据访问。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.stamping import StampingTailorWeldBlank
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.stamping_tailor_weld_blank_dto import (
    TailorWeldBlankPatch,
    TailorWeldBlankWrite,
)

logger = logging.getLogger("repository.stamping.tailor_weld_blank")


class StampingTailorWeldBlankRepository:
    """拼焊子片 CRUD / 按父件批量替换。"""

    def get_by_id(self, db: Session, blank_id: int) -> StampingTailorWeldBlank | None:
        return (
            db.query(StampingTailorWeldBlank)
            .filter(StampingTailorWeldBlank.id == blank_id)
            .first()
        )

    def list_by_part_id(
        self,
        db: Session,
        part_id: int,
    ) -> list[StampingTailorWeldBlank]:
        return (
            db.query(StampingTailorWeldBlank)
            .filter(StampingTailorWeldBlank.part_id == part_id)
            .order_by(StampingTailorWeldBlank.blank_seq.asc())
            .all()
        )

    def count_by_part_id(self, db: Session, part_id: int) -> int:
        return (
            db.query(StampingTailorWeldBlank)
            .filter(StampingTailorWeldBlank.part_id == part_id)
            .count()
        )

    def get_by_part_and_seq(
        self,
        db: Session,
        part_id: int,
        blank_seq: int,
    ) -> StampingTailorWeldBlank | None:
        return (
            db.query(StampingTailorWeldBlank)
            .filter(
                StampingTailorWeldBlank.part_id == part_id,
                StampingTailorWeldBlank.blank_seq == blank_seq,
            )
            .first()
        )

    def create(self, db: Session, data: TailorWeldBlankWrite) -> StampingTailorWeldBlank:
        blank = model_from_payload(StampingTailorWeldBlank, data)
        db.add(blank)
        db.commit()
        db.refresh(blank)
        logger.info(
            "创建拼焊子片: id=%s part_id=%s blank_seq=%s",
            blank.id,
            blank.part_id,
            blank.blank_seq,
        )
        return blank

    def update(
        self,
        db: Session,
        blank_id: int,
        update_data: TailorWeldBlankPatch,
    ) -> StampingTailorWeldBlank | None:
        blank = self.get_by_id(db, blank_id)
        if blank is None:
            return None
        apply_payload_fields(blank, update_data)
        db.commit()
        db.refresh(blank)
        logger.info("更新拼焊子片: id=%s", blank_id)
        return blank

    def delete(self, db: Session, blank_id: int) -> bool:
        blank = self.get_by_id(db, blank_id)
        if blank is None:
            return False
        db.delete(blank)
        db.commit()
        logger.info("删除拼焊子片: id=%s", blank_id)
        return True

    def delete_by_part_id(self, db: Session, part_id: int) -> int:
        """删除某父件下全部子片并提交。"""
        count = (
            db.query(StampingTailorWeldBlank)
            .filter(StampingTailorWeldBlank.part_id == part_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("按父件清空拼焊子片: part_id=%s count=%s", part_id, count)
        return int(count)

    def replace_by_part_id(
        self,
        db: Session,
        part_id: int,
        payloads: list[TailorWeldBlankWrite],
    ) -> list[StampingTailorWeldBlank]:
        """删除父件下旧子片后批量写入新子片（单事务提交）。"""
        db.query(StampingTailorWeldBlank).filter(
            StampingTailorWeldBlank.part_id == part_id
        ).delete(synchronize_session=False)
        blanks = [model_from_payload(StampingTailorWeldBlank, row) for row in payloads]
        db.add_all(blanks)
        db.commit()
        for blank in blanks:
            db.refresh(blank)
        blanks.sort(key=lambda row: row.blank_seq)
        logger.info(
            "整组替换拼焊子片: part_id=%s count=%s",
            part_id,
            len(blanks),
        )
        return blanks

    def bulk_create(
        self,
        db: Session,
        data_list: list[TailorWeldBlankWrite],
    ) -> list[StampingTailorWeldBlank]:
        """批量创建（不提交事务，由调用方管理）。"""
        blanks = [model_from_payload(StampingTailorWeldBlank, row) for row in data_list]
        db.add_all(blanks)
        logger.info("批量创建拼焊子片: %s", len(blanks))
        return blanks
