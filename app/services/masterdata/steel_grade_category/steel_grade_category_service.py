"""牌号分类档案 Service。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.steel_grade_category import (
    CANONICAL_CATEGORIES,
    CANONICAL_CATEGORY_NAMES,
    normalize_category_name,
    seq_for_category,
)
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.masterdata.steel_grade_category import SteelGradeCategoryRepository
from app.schemas.dto.steel_grade_category_dto import (
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

logger = logging.getLogger("service.steel_grade_category")


class SteelGradeCategoryService:
    """牌号分类手工 CRUD 与只读查询。"""

    def __init__(self) -> None:
        self.repository = SteelGradeCategoryRepository()

    def list_canonical_categories(self) -> list[SteelGradeCategoryOptionVO]:
        return [
            SteelGradeCategoryOptionVO(category_seq=seq, category_name=name)
            for seq, name in CANONICAL_CATEGORIES
        ]

    def list_grades_for_filter(
        self,
        db: Session,
        *,
        category_name: str,
        grade: str | None = None,
    ) -> list[str]:
        name = normalize_category_name(category_name)
        if name is None or name not in CANONICAL_CATEGORY_NAMES:
            raise BusinessException("分类无效，请选择冷轧、镀锌或酸洗")
        return self.repository.list_grade_values(
            db,
            category_name=name,
            grade=(grade or "").strip() or None,
        )

    def paginate(
        self, db: Session, query: SteelGradeCategoryQuery
    ) -> tuple[list[SteelGradeCategoryVO], int]:
        skip = (query.page - 1) * query.size
        records, total = self.repository.paginate(
            db,
            grade=query.grade,
            category_name=query.category_name,
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

    def require_existing_grades(self, db: Session, grades: list[str]) -> None:
        """下游写入前校验：非空牌号必须已在档案。不插行。"""
        cleaned = sorted({(item or "").strip() for item in grades if (item or "").strip()})
        if not cleaned:
            return
        mapped = self.map_grades(db, cleaned)
        missing = [grade for grade in cleaned if grade not in mapped]
        if not missing:
            return
        sample = "、".join(missing[:10])
        extra = f" 等 {len(missing)} 个" if len(missing) > 10 else ""
        raise BusinessException(f"牌号未在分类档案中，请先到主数据补档：{sample}{extra}")

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
                    category_seq=self._seq_for_canonical(category_name),
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
            patch["category_seq"] = self._seq_for_canonical(category_name)
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
        except IntegrityError:
            db.rollback()
            raise BusinessException("仍被引用，不能删除") from None
        except Exception:
            db.rollback()
            logger.exception("删除牌号分类失败: id=%s", record_id)
            raise

    def _require_canonical(self, raw: str) -> str:
        name = normalize_category_name(raw)
        if name is None or name not in CANONICAL_CATEGORY_NAMES:
            raise BusinessException(f"大类必须是冷轧、镀锌或酸洗，收到：{raw}")
        return name

    def _seq_for_canonical(self, category_name: str) -> int:
        seq = seq_for_category(category_name)
        if seq is None:
            raise BusinessException(f"大类必须是冷轧、镀锌或酸洗，收到：{category_name}")
        return seq
