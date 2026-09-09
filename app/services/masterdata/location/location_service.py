"""基地主数据 Service。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.location import Location
from app.repositories.masterdata.location import LocationRepository
from app.schemas.dto.location_dto import (
    LocationAliasCreateDTO,
    LocationAliasInsert,
    LocationCreateDTO,
    LocationInsert,
    LocationPatch,
    LocationUpdateDTO,
)
from app.schemas.vo.location_vo import LocationVO
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.location")

_PAGE_HINT = "请到基地页手工增加或启用（#/location）"


class LocationService:
    """基地 CRUD 与解析契约。"""

    def __init__(self) -> None:
        self.repository = LocationRepository()

    def list_all(self, db: Session) -> list[LocationVO]:
        return [self._to_vo(row) for row in self.repository.list_all(db)]

    def list_enabled(self, db: Session) -> list[str]:
        return [row.location for row in self.repository.list_enabled(db)]

    def list_registered(self, db: Session) -> list[str]:
        return [row.location for row in self.repository.list_all(db)]

    def resolve_canonical(self, db: Session, raw: str) -> str | None:
        text = (raw or "").strip()
        if not text:
            return None
        record = self.repository.get_by_location(db, text)
        if record is not None:
            return record.location
        alias_row = self.repository.get_alias(db, text)
        if alias_row is not None:
            return alias_row.location
        return None

    def require_enabled(self, db: Session, raw: str) -> str:
        canonical = self.resolve_canonical(db, raw)
        if canonical is None:
            raise BusinessException(f"没有这座基地，{_PAGE_HINT}")
        record = self.repository.get_by_location(db, canonical)
        if record is None or not record.is_enabled:
            raise BusinessException(f"基地已禁用，{_PAGE_HINT}")
        return canonical

    def expand_for_query(self, db: Session, raw: str) -> list[str]:
        canonical = self.resolve_canonical(db, raw)
        if canonical is None:
            return []
        record = self.repository.get_by_location(db, canonical)
        if record is None:
            return []
        names = [canonical]
        for alias_row in record.aliases:
            if alias_row.alias not in names:
                names.append(alias_row.alias)
        return names

    def create(
        self,
        db: Session,
        dto: LocationCreateDTO,
        current_user: UserVO,
    ) -> LocationVO:
        name = dto.location
        aliases = dto.aliases
        for alias in aliases:
            if alias == name:
                raise BusinessException("别名不得与规范名相同")
            self._assert_alias_available(db, alias)
        self._assert_canonical_available(db, name)
        audit = audit_create(current_user)
        try:
            record = self.repository.create(
                db,
                LocationInsert(
                    location=name,
                    is_enabled=True,
                    sort_order=self.repository.max_sort_order(db) + 1,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            for alias in aliases:
                self.repository.create_alias(
                    db,
                    LocationAliasInsert(alias=alias, location=record.location),
                )
            db.commit()
            db.refresh(record)
        except IntegrityError:
            db.rollback()
            raise BusinessException(f"基地已存在：{name}", code=409) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建基地失败")
            raise
        return self._to_vo(self.repository.get_by_location(db, record.location) or record)

    def update(
        self,
        db: Session,
        location: str,
        dto: LocationUpdateDTO,
        current_user: UserVO,
    ) -> LocationVO:
        record = self._require_row(db, location)
        audit = audit_update(current_user)
        patch: LocationPatch = {
            "is_enabled": dto.is_enabled,
            "updated_by": audit["updated_by"],
        }
        try:
            self.repository.apply_patch(db, record, patch)
            db.commit()
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新基地失败")
            raise
        refreshed = self.repository.get_by_location(db, record.location)
        if refreshed is None:
            raise NotFoundException("基地不存在")
        return self._to_vo(refreshed)

    def delete(self, db: Session, location: str) -> None:
        record = self._require_row(db, location)
        try:
            self.repository.delete(db, record)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException("仍被引用，不能删除") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除基地失败")
            raise

    def add_alias(
        self,
        db: Session,
        location: str,
        dto: LocationAliasCreateDTO,
        current_user: UserVO,
    ) -> LocationVO:
        record = self._require_row(db, location)
        alias = dto.alias
        self._assert_alias_available(db, alias)
        try:
            self.repository.create_alias(
                db,
                LocationAliasInsert(alias=alias, location=record.location),
            )
            audit = audit_update(current_user)
            self.repository.apply_patch(
                db,
                record,
                LocationPatch(updated_by=audit["updated_by"]),
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
        refreshed = self.repository.get_by_location(db, record.location)
        if refreshed is None:
            raise NotFoundException("基地不存在")
        return self._to_vo(refreshed)

    def delete_alias(
        self,
        db: Session,
        location: str,
        alias: str,
        current_user: UserVO,
    ) -> LocationVO:
        record = self._require_row(db, location)
        alias_text = (alias or "").strip()
        alias_row = self.repository.get_alias(db, alias_text)
        if alias_row is None or alias_row.location != record.location:
            raise NotFoundException("别名不存在")
        try:
            self.repository.delete_alias(db, alias_row)
            audit = audit_update(current_user)
            self.repository.apply_patch(
                db,
                record,
                LocationPatch(updated_by=audit["updated_by"]),
            )
            db.commit()
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除别名失败")
            raise
        refreshed = self.repository.get_by_location(db, record.location)
        if refreshed is None:
            raise NotFoundException("基地不存在")
        return self._to_vo(refreshed)

    def _require_row(self, db: Session, location: str) -> Location:
        name = (location or "").strip()
        record = self.repository.get_by_location(db, name)
        if record is None:
            raise NotFoundException("基地不存在")
        return record

    def _assert_canonical_available(self, db: Session, name: str) -> None:
        if self.repository.get_by_location(db, name) is not None:
            raise BusinessException(f"基地已存在：{name}", code=409)
        if self.repository.get_alias(db, name) is not None:
            raise BusinessException("规范名不得等于已有别名", code=409)

    def _assert_alias_available(self, db: Session, name: str) -> None:
        if self.repository.get_by_location(db, name) is not None:
            raise BusinessException("别名不得等于已有规范名", code=409)
        if self.repository.get_alias(db, name) is not None:
            raise BusinessException(f"别名已存在：{name}", code=409)

    def _to_vo(self, row: Location) -> LocationVO:
        return LocationVO(
            location=row.location,
            is_enabled=row.is_enabled,
            sort_order=row.sort_order,
            aliases=[item.alias for item in row.aliases],
            created_by=row.created_by,
            updated_by=row.updated_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
