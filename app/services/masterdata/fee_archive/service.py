"""费用档案：本页 CRUD 与空库种子。不查询计费表。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER, audit_create, audit_update
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.fee_archive import FeeArchive
from app.repositories.masterdata.fee_archive import FeeArchiveRepository
from app.schemas.dto.fee_archive_dto import (
    FeeArchiveCreate,
    FeeArchiveInsert,
    FeeArchivePatch,
    FeeArchiveQuery,
    FeeArchiveUpdate,
)
from app.schemas.vo.fee_archive_vo import FeeArchiveVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.fee_archive.seed import FEE_ARCHIVE_SEEDS
from app.services.settings.schema_comment.service import STILL_REFERENCED, ensure_deletable

logger = logging.getLogger("service.fee_archive")


class FeeArchiveService:
    """费用档案维护。"""

    def __init__(self) -> None:
        self.repository = FeeArchiveRepository()

    def ensure_seed_if_empty(self, db: Session) -> None:
        if self.repository.count(db) > 0:
            return
        audit = audit_create(SYSTEM_USER)
        for seed in FEE_ARCHIVE_SEEDS:
            self.repository.create(
                db,
                FeeArchiveInsert(
                    code=seed.code,
                    name=seed.name,
                    charge_basis=seed.charge_basis,
                    charge_rate=seed.charge_rate,
                    sort_order=seed.sort_order,
                    is_enabled=True,
                    remark=None,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
        db.commit()
        logger.info("已写入费用档案种子 %s 行", len(FEE_ARCHIVE_SEEDS))

    def ensure_missing_seed_fees(self, db: Session) -> tuple[str, ...]:
        """种子里有、库里没有的费用补一行。不改已有费率。"""
        audit = audit_create(SYSTEM_USER)
        added: list[str] = []
        for seed in FEE_ARCHIVE_SEEDS:
            if self.repository.get_by_code(db, seed.code) is not None:
                continue
            if self.repository.get_by_name(db, seed.name) is not None:
                logger.warning("费用种子跳过，名称已被占用：%s", seed.name)
                continue
            self.repository.create(
                db,
                FeeArchiveInsert(
                    code=seed.code,
                    name=seed.name,
                    charge_basis=seed.charge_basis,
                    charge_rate=seed.charge_rate,
                    sort_order=seed.sort_order,
                    is_enabled=True,
                    remark=None,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            added.append(seed.code)
        if not added:
            return ()
        db.commit()
        logger.info("已补费用档案种子 %s", ", ".join(added))
        return tuple(added)

    def list_page(self, db: Session, query: FeeArchiveQuery) -> tuple[list[FeeArchiveVO], int]:
        skip = (query.page - 1) * query.size
        rows, total = self.repository.paginate(
            db,
            keyword=query.q,
            is_enabled=query.is_enabled,
            skip=skip,
            limit=query.size,
        )
        return [FeeArchiveVO.model_validate(row) for row in rows], total

    def create(self, db: Session, dto: FeeArchiveCreate, current_user: UserVO) -> FeeArchiveVO:
        self._assert_free(db, code=dto.code, name=dto.name, owner_id=None)
        audit = audit_create(current_user)
        try:
            record = self.repository.create(
                db,
                FeeArchiveInsert(
                    code=dto.code,
                    name=dto.name,
                    charge_basis=dto.charge_basis,
                    charge_rate=dto.charge_rate,
                    sort_order=dto.sort_order,
                    is_enabled=True,
                    remark=dto.remark,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise BusinessException("编码或名称已存在", code=409) from exc
        db.refresh(record)
        return FeeArchiveVO.model_validate(record)

    def update(
        self,
        db: Session,
        record_id: int,
        dto: FeeArchiveUpdate,
        current_user: UserVO,
    ) -> FeeArchiveVO:
        record = self._require(db, record_id)
        self._assert_free(db, code=record.code, name=dto.name, owner_id=record.id)
        audit = audit_update(current_user)
        try:
            self.repository.update(
                db,
                record,
                FeeArchivePatch(
                    name=dto.name,
                    charge_basis=dto.charge_basis,
                    charge_rate=dto.charge_rate,
                    sort_order=dto.sort_order,
                    is_enabled=dto.is_enabled,
                    remark=dto.remark,
                    updated_by=audit["updated_by"],
                ),
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise BusinessException("编码或名称已存在", code=409) from exc
        db.refresh(record)
        return FeeArchiveVO.model_validate(record)

    def delete(self, db: Session, record_id: int) -> None:
        record = self._require(db, record_id)
        ensure_deletable(db, "fee_archives", [{"id": record.id}], f"费用档案「{record.name}」")
        try:
            self.repository.delete(db, record)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise BusinessException(STILL_REFERENCED) from exc

    def _require(self, db: Session, record_id: int) -> FeeArchive:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("费用档案不存在")
        return record

    def _assert_free(self, db: Session, *, code: str, name: str, owner_id: int | None) -> None:
        by_code = self.repository.get_by_code(db, code)
        if by_code is not None and by_code.id != owner_id:
            raise BusinessException("编码已存在", code=409)
        by_name = self.repository.get_by_name(db, name)
        if by_name is not None and by_name.id != owner_id:
            raise BusinessException("名称已存在", code=409)
