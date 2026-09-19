"""供应商：Excel 整单导入。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.exceptions.base import BusinessException
from app.parsers.masterdata.supplier_parser import parse_supplier_excel
from app.repositories.masterdata.supplier import SupplierRepository
from app.schemas.dto.supplier_dto import SupplierAliasInsert, SupplierInsert
from app.schemas.vo.supplier_vo import SupplierUploadResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.supplier.identity import (
    assert_abbreviation_available,
    assert_alias_available,
    assert_erp_available,
    assert_identity_distinct,
)

logger = logging.getLogger("service.supplier")


def process_upload(
    repository: SupplierRepository,
    db: Session,
    file_content: bytes,
    current_user: UserVO,
) -> SupplierUploadResultVO:
    parsed = parse_supplier_excel(file_content)
    if parsed.errors:
        raise BusinessException("；".join(parsed.errors))

    errors: list[str] = []
    seen: dict[str, tuple[str, str, frozenset[str]]] = {}
    occupied: dict[str, str] = {}
    pending: list[tuple[SupplierInsert, tuple[str, ...]]] = []
    skipped_count = 0
    audit = audit_create(current_user)

    for row in parsed.rows:
        try:
            assert_identity_distinct(
                row.abbreviation,
                row.full_name,
                row.erp_code,
                list(row.aliases),
            )
        except BusinessException as exc:
            errors.append(f"第 {row.row_number} 行：{exc.message}")
            continue

        signature = (row.abbreviation, row.erp_code, frozenset(row.aliases))
        if row.full_name in seen:
            if seen[row.full_name] == signature:
                skipped_count += 1
                continue
            errors.append(
                f"第 {row.row_number} 行：与文件内已有「{row.full_name}」缩写 / 对外代码 / 别名不一致"
            )
            continue

        tokens = [row.abbreviation, row.full_name, row.erp_code, *row.aliases]
        collision = False
        for token in tokens:
            owner = occupied.get(token)
            if owner is not None and owner != row.full_name:
                errors.append(f"第 {row.row_number} 行：「{token}」与文件内「{owner}」冲突")
                collision = True
                break
        if collision:
            continue

        existing = repository.get_by_full_name(db, row.full_name)
        if existing is not None:
            skipped_count += 1
            seen[row.full_name] = signature
            for token in tokens:
                occupied.setdefault(token, row.full_name)
            continue

        token_error: str | None = None
        try:
            assert_abbreviation_available(repository, db, row.abbreviation)
            assert_erp_available(repository, db, row.erp_code)
            for alias in row.aliases:
                assert_alias_available(repository, db, alias)
        except BusinessException as exc:
            token_error = exc.message
        if token_error:
            errors.append(f"第 {row.row_number} 行：{token_error}")
            continue

        seen[row.full_name] = signature
        for token in tokens:
            occupied[token] = row.full_name
        pending.append(
            (
                SupplierInsert(
                    full_name=row.full_name,
                    abbreviation=row.abbreviation,
                    erp_code=row.erp_code,
                    is_enabled=True,
                    sort_order=0,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
                row.aliases,
            )
        )

    if errors:
        raise BusinessException("；".join(errors))

    try:
        next_sort = repository.max_sort_order(db) + 1
        for offset, (payload, aliases) in enumerate(pending):
            payload.sort_order = next_sort + offset
            record = repository.create(db, payload)
            for alias in aliases:
                repository.create_alias(
                    db,
                    SupplierAliasInsert(alias=alias, full_name=record.full_name),
                )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BusinessException("该全称已有供应商") from None
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("导入供应商失败")
        raise
    return SupplierUploadResultVO(
        created_count=len(pending),
        skipped_count=skipped_count,
    )
