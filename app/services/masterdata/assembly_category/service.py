"""总成分类：本页 CRUD 与空库种子。不查询计费表。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER, audit_create, audit_update
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.assembly_category import AssemblyCategory
from app.repositories.masterdata.assembly_category import AssemblyCategoryRepository
from app.schemas.dto.assembly_category_dto import (
    AssemblyCategoryCreate,
    AssemblyCategoryInsert,
    AssemblyCategoryPatch,
    AssemblyCategoryQuery,
    AssemblyCategoryUpdate,
)
from app.schemas.vo.assembly_category_vo import AssemblyCategoryVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.assembly_category.seed import ASSEMBLY_CATEGORY_SEEDS
from app.services.settings.schema_comment.service import STILL_REFERENCED, ensure_deletable

logger = logging.getLogger("service.assembly_category")


class AssemblyCategoryService:
    """总成分类维护。"""

    def __init__(self) -> None:
        self.repository = AssemblyCategoryRepository()

    def ensure_seed_if_empty(self, db: Session) -> None:
        if self.repository.count(db) > 0:
            return
        audit = audit_create(SYSTEM_USER)
        for seed in ASSEMBLY_CATEGORY_SEEDS:
            self.repository.create(
                db,
                AssemblyCategoryInsert(
                    code=seed.code,
                    name=seed.name,
                    sort_order=seed.sort_order,
                    is_enabled=True,
                    remark=None,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
        db.commit()
        logger.info("已写入总成分类种子 %s 行", len(ASSEMBLY_CATEGORY_SEEDS))

    def list_page(
        self,
        db: Session,
        query: AssemblyCategoryQuery,
    ) -> tuple[list[AssemblyCategoryVO], int]:
        skip = (query.page - 1) * query.size
        rows, total = self.repository.paginate(
            db,
            keyword=query.q,
            is_enabled=query.is_enabled,
            skip=skip,
            limit=query.size,
        )
        return [AssemblyCategoryVO.model_validate(row) for row in rows], total

    def create(
        self,
        db: Session,
        dto: AssemblyCategoryCreate,
        current_user: UserVO,
    ) -> AssemblyCategoryVO:
        self._assert_free(db, code=dto.code, name=dto.name, owner_id=None)
        audit = audit_create(current_user)
        try:
            record = self.repository.create(
                db,
                AssemblyCategoryInsert(
                    code=dto.code,
                    name=dto.name,
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
        return AssemblyCategoryVO.model_validate(record)

    def update(
        self,
        db: Session,
        record_id: int,
        dto: AssemblyCategoryUpdate,
        current_user: UserVO,
    ) -> AssemblyCategoryVO:
        record = self._require(db, record_id)
        self._assert_free(db, code=record.code, name=dto.name, owner_id=record.id)
        audit = audit_update(current_user)
        try:
            self.repository.update(
                db,
                record,
                AssemblyCategoryPatch(
                    name=dto.name,
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
        return AssemblyCategoryVO.model_validate(record)

    def delete(self, db: Session, record_id: int) -> None:
        record = self._require(db, record_id)
        ensure_deletable(
            db,
            "assembly_categories",
            [{"id": record.id}],
            f"总成分类「{record.name}」",
        )
        try:
            self.repository.delete(db, record)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise BusinessException(STILL_REFERENCED) from exc

    def _require(self, db: Session, record_id: int) -> AssemblyCategory:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("总成分类不存在")
        return record

    def _assert_free(self, db: Session, *, code: str, name: str, owner_id: int | None) -> None:
        by_code = self.repository.get_by_code(db, code)
        if by_code is not None and by_code.id != owner_id:
            raise BusinessException("编码已存在", code=409)
        by_name = self.repository.get_by_name(db, name)
        if by_name is not None and by_name.id != owner_id:
            raise BusinessException("名称已存在", code=409)
