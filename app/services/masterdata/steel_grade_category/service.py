"""牌号分类档案 Service。"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import NoReturn

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER, audit_create, display_name
from app.common.steel_grade import grade_match_key, stored_grade
from app.common.steel_grade_category import (
    CANONICAL_CATEGORIES,
    CANONICAL_CATEGORY_NAMES,
    normalize_category_name,
    seq_for_category,
)
from app.exceptions.base import BusinessException, NotFoundException
from app.parsers.masterdata.steel_grade_category_parser import parse_steel_grade_category_excel
from app.repositories.masterdata.steel_grade_category.steel_grade_category_repository import (
    SteelGradeCategoryRepository,
)
from app.schemas.dto.steel_grade_category_dto import (
    SteelGradeCategoryCreate,
    SteelGradeCategoryInsert,
    SteelGradeCategoryPatch,
    SteelGradeCategoryQuery,
    SteelGradeCategoryUpdate,
)
from app.schemas.vo.steel_grade_category_vo import (
    SteelGradeCategoryOptionVO,
    SteelGradeCategoryUploadResultVO,
    SteelGradeCategoryVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.steel_grade_category.catalog import (
    build_template as build_catalog_template,
)
from app.services.masterdata.steel_grade_category.seed import SEED_STEEL_GRADE_CATEGORIES
from app.services.settings.foreign_key.service import STILL_REFERENCED, ensure_deletable

logger = logging.getLogger("service.steel_grade_category")


class SteelGradeCategoryService:
    """牌号分类手工 CRUD、同步 Excel 与只读查询。"""

    def __init__(self) -> None:
        self.repository = SteelGradeCategoryRepository()

    def build_template(self) -> tuple[bytes, str]:
        return build_catalog_template()

    def process_upload(
        self,
        db: Session,
        file_content: bytes,
        current_user: UserVO,
    ) -> SteelGradeCategoryUploadResultVO:
        """同步导入：已有牌号跳过；大类不一致则整单拒绝，不静默改大类。"""
        parsed = parse_steel_grade_category_excel(file_content)
        if parsed.errors:
            raise BusinessException("；".join(parsed.errors))
        if not parsed.rows:
            raise BusinessException("没有可导入的牌号行")

        errors: list[str] = []
        pending: list[SteelGradeCategoryInsert] = []
        seen_keys: dict[str, str] = {}
        skipped_count = 0
        audit = audit_create(current_user)

        for row in parsed.rows:
            try:
                category_name = self._require_canonical(row.category_name)
            except BusinessException as exc:
                errors.append(f"第 {row.row_number} 行：{exc.message}")
                continue
            grade = stored_grade(row.grade)
            if not grade:
                errors.append(f"第 {row.row_number} 行：牌号不能为空")
                continue
            key = grade_match_key(grade)
            if not key:
                errors.append(f"第 {row.row_number} 行：牌号无效")
                continue
            if key in seen_keys:
                if seen_keys[key] == category_name:
                    skipped_count += 1
                    continue
                errors.append(f"第 {row.row_number} 行：与文件内已有「{grade}」大类不一致")
                continue
            seen_keys[key] = category_name

            existing = self.match_by_grade_key(db, grade)
            if existing is not None:
                if existing.category_name != category_name:
                    errors.append(
                        f"第 {row.row_number} 行：牌号「{existing.grade}」已在档案，"
                        f"大类为「{existing.category_name}」，不能改成「{category_name}」"
                    )
                    continue
                skipped_count += 1
                continue

            pending.append(
                SteelGradeCategoryInsert(
                    grade=grade,
                    category_name=category_name,
                    category_seq=self._seq_for_canonical(category_name),
                    remark=row.remark,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                )
            )

        if errors:
            raise BusinessException("；".join(errors))

        try:
            for payload in pending:
                self.repository.create(db, payload)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException("牌号已存在") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("导入牌号分类失败")
            raise
        return SteelGradeCategoryUploadResultVO(
            created_count=len(pending),
            skipped_count=skipped_count,
        )

    def ensure_seed_if_empty(self, db: Session) -> None:
        """空库首次启动写入现网牌号分类；已有行则不覆盖。"""
        if self.repository.count(db) > 0:
            return
        audit = audit_create(SYSTEM_USER)
        try:
            for grade, category_name in SEED_STEEL_GRADE_CATEGORIES:
                name = self._require_canonical(category_name)
                self.repository.create(
                    db,
                    SteelGradeCategoryInsert(
                        grade=stored_grade(grade),
                        category_name=name,
                        category_seq=self._seq_for_canonical(name),
                        remark=None,
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                    ),
                )
            db.commit()
            logger.info("已初始化牌号分类档案: %s 条", len(SEED_STEEL_GRADE_CATEGORIES))
        except IntegrityError:
            db.rollback()
            logger.exception("初始化牌号分类失败：唯一键冲突")
            raise
        except Exception:
            db.rollback()
            logger.exception("初始化牌号分类失败")
            raise

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

    def match_by_grade_key(
        self,
        db: Session,
        raw: str,
        *,
        exclude_id: int | None = None,
    ) -> SteelGradeCategoryVO | None:
        """
        外部统一匹配：主数据内做 O/o→0 再大写，与档案逐行比较。
        命中返回档案行（库中原文 grade / 大类）；未命中 None。不改录入、不插档。
        """
        key = grade_match_key(raw)
        if not key:
            return None
        hit: SteelGradeCategoryVO | None = None
        for row in self.repository.list_for_export(db):
            if exclude_id is not None and row.id == exclude_id:
                continue
            if grade_match_key(row.grade) != key:
                continue
            vo = SteelGradeCategoryVO.model_validate(row)
            if hit is not None:
                raise BusinessException(
                    "牌号分类档案存在 O/0 冲突："
                    f"{hit.grade} 与 {vo.grade} 视为同一牌号。"
                    "请只保留一行。",
                    code=409,
                )
            hit = vo
        return hit

    def require_matched_grade(self, db: Session, raw: str | None) -> SteelGradeCategoryVO | None:
        """单条写入：空返回 None；非空必须命中档案，落库用返回行的 grade。"""
        key = (raw or "").strip()
        if not key:
            return None
        return self.require_matched_grades(db, [key])[key]

    def bind_stored_grade(self, db: Session, raw: str | None) -> str | None:
        """单条落库值：空→None，非空→档案 grade。"""
        return self.bind_stored_grades(db, [raw])[0]

    def bind_stored_grades(self, db: Session, raws: Sequence[str | None]) -> list[str | None]:
        """与 raws 等长：空→None，非空→档案 grade。缺档整批拒绝。"""
        matched = self.require_matched_grades(db, raws)
        bound: list[str | None] = []
        for raw in raws:
            key = (raw or "").strip()
            if not key:
                bound.append(None)
            else:
                bound.append(matched[key].grade)
        return bound

    def require_matched_grades(
        self, db: Session, grades: Sequence[str | None]
    ) -> dict[str, SteelGradeCategoryVO]:
        """
        下游写入前：非空牌号必须 match_by_grade_key 命中。不插行。
        返回 strip(原文) → 档案行；调用方落库用档案 grade。
        """
        matched: dict[str, SteelGradeCategoryVO] = {}
        missing: list[str] = []
        seen_missing: set[str] = set()
        for raw in grades:
            key = (raw or "").strip()
            if not key or key in matched or key in seen_missing:
                continue
            archive = self.match_by_grade_key(db, key)
            if archive is None:
                seen_missing.add(key)
                missing.append(key)
                continue
            matched[key] = archive
        self._reject_unknown_grades(missing)
        return matched

    def _reject_unknown_grades(self, missing: list[str]) -> None:
        cleaned = [item.strip() for item in missing if (item or "").strip()]
        if cleaned:
            self._raise_missing_grades(cleaned)

    def create(
        self,
        db: Session,
        dto: SteelGradeCategoryCreate,
        current_user: UserVO,
    ) -> SteelGradeCategoryVO:
        grade = stored_grade(dto.grade)
        if not grade:
            raise BusinessException("牌号不能为空")
        category_name = self._require_canonical(dto.category_name)
        existing = self.match_by_grade_key(db, grade)
        if existing is not None:
            raise BusinessException(f"牌号已存在：{existing.grade}", code=409)
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
        new_grade: str | None = None
        if "grade" in dto.model_fields_set:
            new_grade = stored_grade(dto.grade)
            if not new_grade:
                raise BusinessException("牌号不能为空")
            if new_grade != record.grade:
                existing = self.match_by_grade_key(db, new_grade, exclude_id=record.id)
                if existing is not None:
                    raise BusinessException(f"牌号已存在：{existing.grade}", code=409)
                patch["grade"] = new_grade
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
        except IntegrityError:
            db.rollback()
            raise BusinessException(f"牌号已存在：{new_grade or record.grade}", code=409) from None
        except Exception:
            db.rollback()
            logger.exception("更新牌号分类失败: id=%s", record_id)
            raise

    def delete(self, db: Session, record_id: int) -> None:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("牌号分类不存在")
        try:
            ensure_deletable(
                db,
                "steel_grade_categories",
                [{"id": record.id, "grade": record.grade}],
                subject=f"牌号分类「{record.grade}」",
            )
            self.repository.delete(db, record)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException(STILL_REFERENCED) from None
        except Exception:
            db.rollback()
            logger.exception("删除牌号分类失败: id=%s", record_id)
            raise

    def _raise_missing_grades(self, missing: list[str]) -> NoReturn:
        sample = "、".join(missing[:10])
        extra = f"\n共 {len(missing)} 个牌号未在档案中。" if len(missing) > 10 else ""
        raise BusinessException(
            "本次未导入。请到侧栏「主数据 → 牌号分类」点新增，"
            f"把下面牌号补上并保存，再重新上传：\n{sample}{extra}"
        )

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
