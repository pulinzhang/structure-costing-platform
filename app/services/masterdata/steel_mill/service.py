"""钢厂档案：本页 CRUD，以及一次装表的对外解析。"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import NamedTuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER, audit_create, audit_update
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.steel_mill import SteelMill
from app.repositories.masterdata.steel_mill.steel_mill_repository import SteelMillRepository
from app.schemas.dto.steel_mill_dto import (
    SteelMillCreate,
    SteelMillInsert,
    SteelMillPatch,
    SteelMillQuery,
    SteelMillUpdate,
)
from app.schemas.vo.steel_mill_vo import SteelMillChoiceVO, SteelMillVO
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.steel_mill.hit import SteelMillHit
from app.services.masterdata.steel_mill.normalize import mill_lookup_key, normalize_mill_text
from app.services.masterdata.steel_mill.seed import STEEL_MILL_SEEDS
from app.services.settings.schema_comment.service import STILL_REFERENCED, ensure_deletable

logger = logging.getLogger("service.steel_mill")

_PAGE_HINT = "请到钢厂页手工增加（#/steel-mill）"
_ENABLE_HINT = "请到钢厂页启用（#/steel-mill）"
_MISS_LIMIT = 20


class _MillIndex(NamedTuple):
    """一次读出的档案。by_text 用来对原文，by_id 用来显示缩写。"""

    by_text: dict[str, SteelMillHit]
    by_id: dict[int, SteelMillHit]


def _join_clauses(clauses: list[str], hint: str) -> str:
    shown = clauses[:_MISS_LIMIT]
    extra = f"，共 {len(clauses)} 家" if len(clauses) > _MISS_LIMIT else ""
    return f"{'；'.join(shown)}{extra}。{hint}。"


class SteelMillService:
    """钢厂维护与解析。不查询、不更新基准价或加减价。"""

    def __init__(self) -> None:
        self.repository = SteelMillRepository()

    def ensure_seed_if_empty(self, db: Session) -> None:
        if self.repository.count(db) > 0:
            return
        audit = audit_create(SYSTEM_USER)
        for index, seed in enumerate(STEEL_MILL_SEEDS, start=1):
            record = self.repository.create(
                db,
                SteelMillInsert(
                    abbreviation=seed.abbreviation,
                    full_name=seed.full_name,
                    is_enabled=True,
                    sort_order=index,
                    remark=None,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            if seed.aliases:
                self.repository.replace_aliases(db, record.id, list(seed.aliases))
        db.commit()
        logger.info("已写入钢厂种子 %s 家", len(STEEL_MILL_SEEDS))

    def list_page(self, db: Session, query: SteelMillQuery) -> tuple[list[SteelMillVO], int]:
        skip = (query.page - 1) * query.size
        rows, total = self.repository.paginate(
            db,
            keyword=query.q,
            is_enabled=query.is_enabled,
            skip=skip,
            limit=query.size,
        )
        aliases = self.repository.aliases_by_mill(db, [row.id for row in rows])
        return [self._vo(row, aliases.get(row.id, [])) for row in rows], total

    def list_enabled(self, db: Session) -> list[SteelMillChoiceVO]:
        return [
            SteelMillChoiceVO(id=row.id, abbreviation=row.abbreviation, full_name=row.full_name)
            for row in self.repository.list_enabled(db)
        ]

    def create(self, db: Session, dto: SteelMillCreate, current_user: UserVO) -> SteelMillVO:
        aliases = self._checked_aliases(dto.abbreviation, dto.full_name, dto.aliases)
        self._assert_free(db, dto.abbreviation, dto.full_name, aliases, owner_id=None)
        audit = audit_create(current_user)
        try:
            record = self.repository.create(
                db,
                SteelMillInsert(
                    abbreviation=dto.abbreviation,
                    full_name=dto.full_name,
                    is_enabled=True,
                    sort_order=self.repository.max_sort_order(db) + 1,
                    remark=dto.remark,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            self.repository.replace_aliases(db, record.id, aliases)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise BusinessException("钢厂缩写、全称或别名已存在", code=409) from exc
        db.refresh(record)
        return self._vo(record, self.repository.aliases_for(db, record.id))

    def update(
        self,
        db: Session,
        record_id: int,
        dto: SteelMillUpdate,
        current_user: UserVO,
    ) -> SteelMillVO:
        record = self._require(db, record_id)
        aliases = self._checked_aliases(dto.abbreviation, dto.full_name, dto.aliases)
        self._assert_free(
            db,
            dto.abbreviation,
            dto.full_name,
            aliases,
            owner_id=record.id,
        )
        audit = audit_update(current_user)
        try:
            self.repository.update(
                db,
                record,
                SteelMillPatch(
                    abbreviation=dto.abbreviation,
                    full_name=dto.full_name,
                    is_enabled=dto.is_enabled,
                    remark=dto.remark,
                    updated_by=audit["updated_by"],
                ),
            )
            self.repository.replace_aliases(db, record.id, aliases)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise BusinessException("钢厂缩写、全称或别名已存在", code=409) from exc
        db.refresh(record)
        return self._vo(record, self.repository.aliases_for(db, record.id))

    def delete(self, db: Session, record_id: int) -> None:
        record = self._require(db, record_id)
        ensure_deletable(db, "steel_mills", [{"id": record.id}], record.abbreviation)
        try:
            self.repository.delete(db, record)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise BusinessException(STILL_REFERENCED) from exc

    def resolve(self, db: Session, raw: str | None) -> SteelMillHit | None:
        key = mill_lookup_key(raw)
        if not key:
            return None
        return self._table(db).get(key)

    def resolve_many(self, db: Session, raws: Sequence[str | None]) -> dict[str, SteelMillHit]:
        table = self._table(db)
        found: dict[str, SteelMillHit] = {}
        for raw in raws:
            text = normalize_mill_text(raw)
            if not text or text in found:
                continue
            hit = table.get(mill_lookup_key(text))
            if hit is not None:
                found[text] = hit
        return found

    def require_enabled(self, db: Session, raw: str | None) -> SteelMillHit:
        text = normalize_mill_text(raw)
        if not text:
            raise BusinessException(f"钢厂不能为空。{_PAGE_HINT}")
        hit = self.resolve(db, text)
        if hit is None:
            raise BusinessException(f"钢厂「{text}」不存在。{_PAGE_HINT}")
        if not hit.is_enabled:
            raise BusinessException(f"钢厂「{hit.abbreviation}」已停用，不能再选用。{_ENABLE_HINT}")
        return hit

    def require_enabled_many(
        self,
        db: Session,
        raws: Sequence[str | None],
        *,
        places: Sequence[str],
    ) -> dict[str, SteelMillHit]:
        """整本收口。places 与 raws 一一对应，拒绝句带上 Excel 行或 sheet。"""
        table = self._table(db)
        found: dict[str, SteelMillHit] = {}
        missing: list[str] = []
        disabled: list[str] = []
        seen_missing: set[str] = set()
        seen_disabled_ids: set[int] = set()
        blank_seen = False
        for raw, place in zip(raws, places, strict=True):
            text = normalize_mill_text(raw)
            if text in found or text in seen_missing:
                continue
            if not text:
                if not blank_seen:
                    blank_seen = True
                    missing.append(f"钢厂不能为空（{place}）")
                continue
            hit = table.get(mill_lookup_key(text))
            if hit is None:
                seen_missing.add(text)
                missing.append(f"钢厂「{text}」不存在（{place}）")
                continue
            if not hit.is_enabled:
                if hit.id not in seen_disabled_ids:
                    seen_disabled_ids.add(hit.id)
                    disabled.append(f"钢厂「{hit.abbreviation}」已停用，不能再选用（{place}）")
                continue
            found[text] = hit
        if missing or disabled:
            raise BusinessException(self._reject_message(missing, disabled))
        return found

    def filter_id(self, db: Session, raw: str | None) -> int | None:
        """列表筛选用。空表示不筛。对不上档案时返回 0，查询结果为空。"""
        text = normalize_mill_text(raw)
        if not text:
            return None
        hit = self.resolve(db, text)
        if hit is None:
            return 0
        return hit.id

    def hits_by_id(self, db: Session) -> dict[int, SteelMillHit]:
        """列表显示缩写。一次装表。"""
        return self._index(db).by_id

    def _table(self, db: Session) -> dict[str, SteelMillHit]:
        return self._index(db).by_text

    def _index(self, db: Session) -> _MillIndex:
        mills = self.repository.list_all(db)
        aliases = self.repository.list_aliases(db)
        by_id = {
            row.id: SteelMillHit(
                id=row.id,
                abbreviation=row.abbreviation,
                full_name=row.full_name,
                is_enabled=row.is_enabled,
            )
            for row in mills
        }
        by_text: dict[str, SteelMillHit] = {}
        for row in mills:
            hit = by_id[row.id]
            self._put(by_text, row.abbreviation, hit)
            self._put(by_text, row.full_name, hit)
        for alias in aliases:
            alias_hit = by_id.get(alias.steel_mill_id)
            if alias_hit is not None:
                self._put(by_text, alias.alias, alias_hit)
        return _MillIndex(by_text=by_text, by_id=by_id)

    def _put(self, table: dict[str, SteelMillHit], raw: str, hit: SteelMillHit) -> None:
        key = mill_lookup_key(raw)
        if not key:
            return
        current = table.get(key)
        if current is not None and current.id != hit.id:
            raise BusinessException(f"钢厂写法「{raw}」同时属于两家", code=409)
        table[key] = hit

    def _require(self, db: Session, record_id: int) -> SteelMill:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("钢厂不存在")
        return record

    def _checked_aliases(
        self,
        abbreviation: str,
        full_name: str,
        aliases: list[str],
    ) -> list[str]:
        owner_keys = {mill_lookup_key(abbreviation), mill_lookup_key(full_name)}
        seen: set[str] = set()
        cleaned: list[str] = []
        for alias in aliases:
            key = mill_lookup_key(alias)
            if not key or key in owner_keys or key in seen:
                if key in owner_keys:
                    raise BusinessException("别名不能与缩写或全称相同", code=409)
                continue
            seen.add(key)
            cleaned.append(normalize_mill_text(alias))
        return cleaned

    def _assert_free(
        self,
        db: Session,
        abbreviation: str,
        full_name: str,
        aliases: list[str],
        *,
        owner_id: int | None,
    ) -> None:
        table = self._table(db)
        for raw in (abbreviation, full_name, *aliases):
            hit = table.get(mill_lookup_key(raw))
            if hit is not None and hit.id != owner_id:
                raise BusinessException(f"「{raw}」已被占用", code=409)

    def _vo(self, row: SteelMill, aliases: list[str]) -> SteelMillVO:
        vo = SteelMillVO.model_validate(row)
        vo.aliases = aliases
        return vo

    def _reject_message(self, missing: list[str], disabled: list[str]) -> str:
        parts: list[str] = []
        if missing:
            parts.append(_join_clauses(missing, _PAGE_HINT))
        if disabled:
            parts.append(_join_clauses(disabled, _ENABLE_HINT))
        parts.append("本文件未写入。")
        return "".join(parts)
