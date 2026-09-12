"""供应商：列表查询与 CRUD / 别名。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.masterdata.supplier import SupplierRepository
from app.schemas.dto.supplier_dto import (
    SupplierAliasCreateDTO,
    SupplierAliasInsert,
    SupplierCreateDTO,
    SupplierInsert,
    SupplierPatch,
    SupplierQuery,
    SupplierUpdateDTO,
)
from app.schemas.vo.supplier_vo import SupplierChoiceVO, SupplierVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.supplier.identity import (
    assert_abbreviation_available,
    assert_abbreviation_available_for,
    assert_alias_available,
    assert_canonical_available,
    assert_canonical_available_for,
    assert_erp_available,
    assert_erp_available_for,
    assert_identity_distinct,
    lookup_token_owner,
    require_row,
    to_vo,
)

logger = logging.getLogger("service.supplier")


def list_enabled(repository: SupplierRepository, db: Session) -> list[SupplierVO]:
    return [to_vo(row) for row in repository.list_enabled(db)]


def list_enabled_choices(repository: SupplierRepository, db: Session) -> list[SupplierChoiceVO]:
    return [
        SupplierChoiceVO(full_name=row.full_name, abbreviation=row.abbreviation)
        for row in repository.list_enabled(db)
    ]


def search_enabled_choices(
    repository: SupplierRepository,
    db: Session,
    *,
    keyword: str | None,
    page: int,
    size: int,
) -> tuple[list[SupplierChoiceVO], int]:
    skip = (page - 1) * size
    rows, total = repository.paginate(
        db,
        keyword=keyword,
        is_enabled=True,
        skip=skip,
        limit=size,
    )
    return [
        SupplierChoiceVO(full_name=row.full_name, abbreviation=row.abbreviation) for row in rows
    ], total


def list_registered(repository: SupplierRepository, db: Session) -> list[SupplierVO]:
    return [to_vo(row) for row in repository.list_all(db)]


def list_registered_names(repository: SupplierRepository, db: Session) -> list[str]:
    return [row.full_name for row in repository.list_all(db)]


def list_page(
    repository: SupplierRepository,
    db: Session,
    query: SupplierQuery,
) -> tuple[list[SupplierVO], int]:
    skip = (query.page - 1) * query.size
    rows, total = repository.paginate(
        db,
        keyword=query.q,
        is_enabled=query.is_enabled,
        skip=skip,
        limit=query.size,
    )
    return [to_vo(row) for row in rows], total


def create_supplier(
    repository: SupplierRepository,
    db: Session,
    dto: SupplierCreateDTO,
    current_user: UserVO,
) -> SupplierVO:
    assert_identity_distinct(dto.abbreviation, dto.full_name, dto.erp_code, dto.aliases)
    assert_canonical_available(repository, db, dto.full_name)
    assert_abbreviation_available(repository, db, dto.abbreviation)
    assert_erp_available(repository, db, dto.erp_code)
    for alias in dto.aliases:
        assert_alias_available(repository, db, alias)
    audit = audit_create(current_user)
    try:
        record = repository.create(
            db,
            SupplierInsert(
                full_name=dto.full_name,
                abbreviation=dto.abbreviation,
                erp_code=dto.erp_code,
                is_enabled=True,
                sort_order=repository.max_sort_order(db) + 1,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        for alias in dto.aliases:
            repository.create_alias(
                db,
                SupplierAliasInsert(alias=alias, full_name=record.full_name),
            )
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise BusinessException("该工商名称已有供应商") from None
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("创建供应商失败")
        raise
    return to_vo(repository.get_by_full_name(db, record.full_name) or record)


def update_supplier(
    repository: SupplierRepository,
    db: Session,
    full_name: str,
    dto: SupplierUpdateDTO,
    current_user: UserVO,
) -> SupplierVO:
    record = require_row(repository, db, full_name)
    data = dto.model_dump(exclude_unset=True)
    if not data:
        raise BusinessException("没有要更新的字段")
    new_abbreviation = data.get("abbreviation", record.abbreviation)
    new_full_name = data.get("full_name", record.full_name)
    new_erp_code = data.get("erp_code", record.erp_code)
    remaining_aliases = [item.alias for item in record.aliases if item.alias != new_full_name]
    assert_identity_distinct(
        new_abbreviation,
        new_full_name,
        new_erp_code,
        remaining_aliases,
    )
    old_full_name = record.full_name
    renamed = new_full_name != old_full_name
    if renamed:
        assert_canonical_available_for(repository, db, new_full_name, old_full_name)
    if new_abbreviation != record.abbreviation:
        assert_abbreviation_available_for(repository, db, new_abbreviation, old_full_name)
    if new_erp_code != record.erp_code:
        assert_erp_available_for(repository, db, new_erp_code, old_full_name)
    audit = audit_update(current_user)
    try:
        if renamed:
            alias_row = repository.get_alias(db, new_full_name)
            if alias_row is not None and alias_row.full_name == old_full_name:
                repository.delete_alias(db, alias_row)
            repository.update_full_name(db, old_full_name, new_full_name)
            record = require_row(repository, db, new_full_name)
            occupied = lookup_token_owner(repository, db, old_full_name)
            if occupied is not None:
                raise BusinessException("该名称已被占用")
            repository.create_alias(
                db,
                SupplierAliasInsert(alias=old_full_name, full_name=new_full_name),
            )
        patch: SupplierPatch = {"updated_by": audit["updated_by"]}
        if new_abbreviation != record.abbreviation:
            patch["abbreviation"] = new_abbreviation
        if new_erp_code != record.erp_code:
            patch["erp_code"] = new_erp_code
        if "is_enabled" in data:
            patch["is_enabled"] = bool(data["is_enabled"])
        repository.apply_patch(db, record, patch)
        db.commit()
    except IntegrityError:
        db.rollback()
        if renamed:
            raise BusinessException("仍被引用，不能修改") from None
        raise BusinessException("该工商名称已有供应商") from None
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("更新供应商失败")
        raise
    refreshed = repository.get_by_full_name(db, new_full_name)
    if refreshed is None:
        raise NotFoundException("供应商不存在")
    return to_vo(refreshed)


def delete_supplier(repository: SupplierRepository, db: Session, full_name: str) -> None:
    record = require_row(repository, db, full_name)
    try:
        repository.delete(db, record)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException("仍被引用，不能删除") from None
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("删除供应商失败")
        raise


def add_alias(
    repository: SupplierRepository,
    db: Session,
    full_name: str,
    dto: SupplierAliasCreateDTO,
    current_user: UserVO,
) -> SupplierVO:
    record = require_row(repository, db, full_name)
    alias = dto.alias
    assert_alias_available(repository, db, alias)
    try:
        repository.create_alias(
            db,
            SupplierAliasInsert(alias=alias, full_name=record.full_name),
        )
        audit = audit_update(current_user)
        repository.apply_patch(
            db,
            record,
            SupplierPatch(updated_by=audit["updated_by"]),
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException(f"别名已存在：{alias}", code=409) from None
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("新增别名失败")
        raise
    refreshed = repository.get_by_full_name(db, record.full_name)
    if refreshed is None:
        raise NotFoundException("供应商不存在")
    return to_vo(refreshed)


def delete_alias(
    repository: SupplierRepository,
    db: Session,
    full_name: str,
    alias: str,
    current_user: UserVO,
) -> SupplierVO:
    record = require_row(repository, db, full_name)
    alias_text = (alias or "").strip()
    alias_row = repository.get_alias(db, alias_text)
    if alias_row is None or alias_row.full_name != record.full_name:
        raise NotFoundException("别名不存在")
    try:
        repository.delete_alias(db, alias_row)
        audit = audit_update(current_user)
        repository.apply_patch(
            db,
            record,
            SupplierPatch(updated_by=audit["updated_by"]),
        )
        db.commit()
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("删除别名失败")
        raise
    refreshed = repository.get_by_full_name(db, record.full_name)
    if refreshed is None:
        raise NotFoundException("供应商不存在")
    return to_vo(refreshed)
