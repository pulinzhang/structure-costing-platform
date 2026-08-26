"""牌号分类档案 Service。ensure_grades 不 commit，由调用方事务收口。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.yishiyiyi.base_price import SteelBasePriceRepository
from app.repositories.yishiyiyi.steel_grade_category import SteelGradeCategoryRepository
from app.schemas.dto.steel_grade_category_dto import (
    GradeEnsureItem,
    GradeEnsureResult,
    SteelGradeCategoryCreate,
    SteelGradeCategoryInsert,
    SteelGradeCategoryPatch,
    SteelGradeCategoryQuery,
    SteelGradeCategoryUpdate,
)
from app.schemas.vo.steel_grade_category_vo import (
    SteelGradeCategoryOptionVO,
    SteelGradeCategoryVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.yishiyiyi.steel_grade_category.constants import (
    CANONICAL_CATEGORIES,
    CANONICAL_CATEGORY_NAMES,
    SOURCE_BASE_PRICE,
    SOURCE_MANUAL,
    SOURCE_STAMPING_UPLOAD,
    normalize_category_name,
    seq_for_category,
)

logger = logging.getLogger("service.steel_grade_category")


class SteelGradeCategoryService:
    """牌号分类 CRUD 与导入补行。"""

    def __init__(self) -> None:
        self.repository = SteelGradeCategoryRepository()
        self.base_price_repository = SteelBasePriceRepository()

    def list_canonical_categories(self) -> list[SteelGradeCategoryOptionVO]:
        return [
            SteelGradeCategoryOptionVO(category_seq=seq, category_name=name)
            for seq, name in CANONICAL_CATEGORIES
        ]

    def paginate(
        self, db: Session, query: SteelGradeCategoryQuery
    ) -> tuple[list[SteelGradeCategoryVO], int]:
        skip = (query.page - 1) * query.size
        records, total = self.repository.paginate(
            db,
            grade=query.grade,
            category_name=query.category_name,
            uncategorized=query.uncategorized,
            skip=skip,
            limit=query.size,
        )
        return [SteelGradeCategoryVO.model_validate(row) for row in records], total

    def get_by_id(self, db: Session, record_id: int) -> SteelGradeCategoryVO:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("牌号分类不存在")
        return SteelGradeCategoryVO.model_validate(record)

    def get_by_grade(self, db: Session, grade: str) -> SteelGradeCategoryVO | None:
        record = self.repository.get_by_grade(db, (grade or "").strip())
        if record is None:
            return None
        return SteelGradeCategoryVO.model_validate(record)

    def map_grades(self, db: Session, grades: list[str]) -> dict[str, SteelGradeCategoryVO]:
        cleaned = [(item or "").strip() for item in grades if (item or "").strip()]
        records = self.repository.list_by_grades(db, cleaned)
        return {row.grade: SteelGradeCategoryVO.model_validate(row) for row in records}

    def create(
        self,
        db: Session,
        dto: SteelGradeCategoryCreate,
        current_user: UserVO,
    ) -> SteelGradeCategoryVO:
        grade = dto.grade.strip()
        category_name = self._require_canonical(dto.category_name)
        if self.repository.get_by_grade(db, grade) is not None:
            raise BusinessException(f"牌号已存在：{grade}", code=409)
        audit = audit_create(current_user)
        try:
            record = self.repository.create(
                db,
                SteelGradeCategoryInsert(
                    grade=grade,
                    category_name=category_name,
                    category_seq=seq_for_category(category_name),
                    source=SOURCE_MANUAL,
                    remark=dto.remark,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            db.commit()
            return SteelGradeCategoryVO.model_validate(record)
        except IntegrityError:
            db.rollback()
            raise BusinessException(f"牌号已存在：{grade}", code=409) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建牌号分类失败: grade=%s", grade)
            raise

    def update(
        self,
        db: Session,
        record_id: int,
        dto: SteelGradeCategoryUpdate,
        current_user: UserVO,
    ) -> SteelGradeCategoryVO:
        if not dto.model_fields_set:
            raise BusinessException("没有提供任何更新字段")
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("牌号分类不存在")
        patch: SteelGradeCategoryPatch = {"updated_by": display_name(current_user)}
        if "category_name" in dto.model_fields_set:
            if dto.category_name is None:
                raise BusinessException("大类不能为空")
            category_name = self._require_canonical(dto.category_name)
            patch["category_name"] = category_name
            patch["category_seq"] = seq_for_category(category_name)
        if "remark" in dto.model_fields_set:
            patch["remark"] = dto.remark
        try:
            record = self.repository.apply_patch(db, record, patch)
            db.commit()
            return SteelGradeCategoryVO.model_validate(record)
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新牌号分类失败: id=%s", record_id)
            raise

    def delete(self, db: Session, record_id: int) -> None:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("牌号分类不存在")
        try:
            self.repository.delete(db, record)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("删除牌号分类失败: id=%s", record_id)
            raise

    def ensure_grades(
        self,
        db: Session,
        items: list[GradeEnsureItem],
        *,
        source: str,
        current_user: UserVO,
    ) -> GradeEnsureResult:
        """缺 grade 则插入。不 commit。"""
        merged, batch_conflicts = self._merge_batch(items)
        if not merged:
            return GradeEnsureResult(conflicts=batch_conflicts or None)

        existing = {
            row.grade: row for row in self.repository.list_by_grades(db, list(merged.keys()))
        }
        lookup_grades = [
            grade
            for grade, item in merged.items()
            if source == SOURCE_STAMPING_UPLOAD and not item.category_name
        ]
        from_base = self.base_price_repository.map_most_frequent_category_by_grades(
            db, lookup_grades
        )

        audit = audit_create(current_user)
        inserted = 0
        claimed = 0
        skipped = 0
        conflicts = list(batch_conflicts)

        for grade, item in merged.items():
            incoming = self._canonical_or_none(item.category_name)
            if incoming is None and source == SOURCE_STAMPING_UPLOAD:
                incoming = self._canonical_or_none(from_base.get(grade))

            record = existing.get(grade)
            if record is None:
                if source != SOURCE_STAMPING_UPLOAD and incoming is None:
                    skipped += 1
                    continue
                self.repository.create(
                    db,
                    SteelGradeCategoryInsert(
                        grade=grade,
                        category_name=incoming,
                        category_seq=seq_for_category(incoming),
                        source=source,
                        remark=None,
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                    ),
                )
                inserted += 1
                continue

            if record.category_name is None and incoming is not None:
                self.repository.apply_patch(
                    db,
                    record,
                    {
                        "category_name": incoming,
                        "category_seq": seq_for_category(incoming),
                        "updated_by": audit["updated_by"],
                    },
                )
                claimed += 1
                continue

            if (
                incoming is not None
                and record.category_name is not None
                and incoming != record.category_name
            ):
                conflicts.append(f"{grade} 档案={record.category_name} 本次={incoming}，未覆盖")
            skipped += 1

        return GradeEnsureResult(
            inserted_count=inserted,
            claimed_count=claimed,
            skipped_count=skipped,
            conflicts=conflicts or None,
        )

    def backfill_from_base_prices(self, db: Session, current_user: UserVO) -> GradeEnsureResult:
        pairs = self.base_price_repository.list_distinct_grade_categories(db)
        items = [
            GradeEnsureItem(grade=grade, category_name=category_name)
            for grade, category_name in pairs
        ]
        result = self.ensure_grades(db, items, source=SOURCE_BASE_PRICE, current_user=current_user)
        db.commit()
        return result

    def _require_canonical(self, raw: str) -> str:
        name = normalize_category_name(raw)
        if name is None or name not in CANONICAL_CATEGORY_NAMES:
            raise BusinessException(f"大类必须是冷轧、镀锌或酸洗，收到：{raw}")
        return name

    def _canonical_or_none(self, raw: str | None) -> str | None:
        name = normalize_category_name(raw)
        if name is None:
            return None
        if name not in CANONICAL_CATEGORY_NAMES:
            return None
        return name

    def _merge_batch(
        self, items: list[GradeEnsureItem]
    ) -> tuple[dict[str, GradeEnsureItem], list[str]]:
        merged: dict[str, GradeEnsureItem] = {}
        conflicts: list[str] = []
        for item in items:
            grade = (item.grade or "").strip()
            if not grade:
                continue
            category = self._canonical_or_none(item.category_name)
            incoming = GradeEnsureItem(grade=grade, category_name=category)
            previous = merged.get(grade)
            if previous is None:
                merged[grade] = incoming
                continue
            if (
                previous.category_name
                and incoming.category_name
                and previous.category_name != incoming.category_name
            ):
                conflicts.append(
                    f"{grade} 本批次两种大类：{previous.category_name} / {incoming.category_name}"
                )
            elif previous.category_name is None and incoming.category_name is not None:
                merged[grade] = incoming
        return merged, conflicts
