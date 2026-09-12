"""供应商：解析契约与身份占用断言。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.supplier import Supplier
from app.repositories.masterdata.supplier import SupplierRepository
from app.schemas.vo.supplier_vo import SupplierVO

PAGE_HINT = "请到供应商一览表手工增加或上传（#/supplier-list）"
DISABLED_HINT = "请到供应商一览表启用（#/supplier-list）"


def to_vo(row: Supplier) -> SupplierVO:
    return SupplierVO(
        full_name=row.full_name,
        abbreviation=row.abbreviation,
        erp_code=row.erp_code,
        is_enabled=row.is_enabled,
        sort_order=row.sort_order,
        aliases=[item.alias for item in row.aliases],
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def require_row(repository: SupplierRepository, db: Session, full_name: str) -> Supplier:
    name = (full_name or "").strip()
    record = repository.get_by_full_name(db, name)
    if record is None:
        raise NotFoundException("供应商不存在")
    return record


def assert_identity_distinct(
    abbreviation: str,
    full_name: str,
    erp_code: str,
    aliases: list[str],
) -> None:
    tokens = [abbreviation, full_name, erp_code, *aliases]
    seen: set[str] = set()
    for token in tokens:
        if token in seen:
            raise BusinessException("缩写、工商名称、ERP 代码与别名不得相同")
        seen.add(token)


def lookup_token_owner(repository: SupplierRepository, db: Session, token: str) -> str | None:
    by_full = repository.get_by_full_name(db, token)
    if by_full is not None:
        return by_full.full_name
    by_abbr = repository.get_by_abbreviation(db, token)
    if by_abbr is not None:
        return by_abbr.full_name
    by_erp = repository.get_by_erp_code(db, token)
    if by_erp is not None:
        return by_erp.full_name
    alias_row = repository.get_alias(db, token)
    if alias_row is not None:
        return alias_row.full_name
    return None


def assert_canonical_available(repository: SupplierRepository, db: Session, name: str) -> None:
    owner = lookup_token_owner(repository, db, name)
    if owner is not None:
        raise BusinessException("该工商名称已有供应商")


def assert_canonical_available_for(
    repository: SupplierRepository, db: Session, name: str, owner: str
) -> None:
    current = lookup_token_owner(repository, db, name)
    if current is not None and current != owner:
        raise BusinessException("该工商名称已有供应商")


def assert_abbreviation_available(repository: SupplierRepository, db: Session, name: str) -> None:
    if lookup_token_owner(repository, db, name) is not None:
        raise BusinessException("该缩写已被占用")


def assert_abbreviation_available_for(
    repository: SupplierRepository, db: Session, name: str, owner: str
) -> None:
    current = lookup_token_owner(repository, db, name)
    if current is not None and current != owner:
        raise BusinessException("该缩写已被占用")


def assert_erp_available(repository: SupplierRepository, db: Session, name: str) -> None:
    if lookup_token_owner(repository, db, name) is not None:
        raise BusinessException("该 ERP 代码已被占用")


def assert_erp_available_for(
    repository: SupplierRepository, db: Session, name: str, owner: str
) -> None:
    current = lookup_token_owner(repository, db, name)
    if current is not None and current != owner:
        raise BusinessException("该 ERP 代码已被占用")


def assert_alias_available(repository: SupplierRepository, db: Session, name: str) -> None:
    if lookup_token_owner(repository, db, name) is not None:
        raise BusinessException("别名不得等于已有缩写、工商名称、ERP 代码或别名")


def resolve_canonical(repository: SupplierRepository, db: Session, raw: str) -> str | None:
    text = (raw or "").strip()
    if not text:
        return None
    by_full = repository.get_by_full_name(db, text)
    if by_full is not None:
        return by_full.full_name
    by_abbr = repository.get_by_abbreviation(db, text)
    if by_abbr is not None:
        return by_abbr.full_name
    by_erp = repository.get_by_erp_code(db, text)
    if by_erp is not None:
        return by_erp.full_name
    alias_row = repository.get_alias(db, text)
    if alias_row is not None:
        return alias_row.full_name
    return None


def require_enabled(repository: SupplierRepository, db: Session, raw: str) -> str:
    canonical = resolve_canonical(repository, db, raw)
    if canonical is None:
        raise BusinessException(f"没有该供应商，{PAGE_HINT}")
    record = repository.get_by_full_name(db, canonical)
    if record is None or not record.is_enabled:
        raise BusinessException(f"供应商已禁用，{DISABLED_HINT}")
    return canonical


def expand_for_query(repository: SupplierRepository, db: Session, raw: str) -> list[str]:
    canonical = resolve_canonical(repository, db, raw)
    if canonical is None:
        return []
    record = repository.get_by_full_name(db, canonical)
    if record is None:
        return []
    names = [canonical]
    if record.abbreviation not in names:
        names.append(record.abbreviation)
    if record.erp_code not in names:
        names.append(record.erp_code)
    for alias_row in record.aliases:
        if alias_row.alias not in names:
            names.append(alias_row.alias)
    return names


def names_for_query(
    repository: SupplierRepository, db: Session, raw: str | None
) -> list[str] | None:
    """None = 不筛；空列表 = 解析失败；非空 = IN 列表。"""
    text = (raw or "").strip()
    if not text:
        return None
    return expand_for_query(repository, db, text)


def is_registered(repository: SupplierRepository, db: Session, full_name: str) -> bool:
    name = (full_name or "").strip()
    if not name:
        return False
    return repository.get_by_full_name(db, name) is not None
