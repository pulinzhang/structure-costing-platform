"""牌号分类档案 Repository。"""

from sqlalchemy.orm import Query, Session

from app.models.masterdata.steel_grade_category import SteelGradeCategory
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.steel_grade_category_dto import (
    SteelGradeCategoryInsert,
    SteelGradeCategoryPatch,
)


class SteelGradeCategoryRepository:
    """牌号分类数据访问。"""

    def count(self, db: Session) -> int:
        return db.query(SteelGradeCategory).count()

    def get_by_id(self, db: Session, record_id: int) -> SteelGradeCategory | None:
        return db.query(SteelGradeCategory).filter(SteelGradeCategory.id == record_id).first()

    def get_by_grade(self, db: Session, grade: str) -> SteelGradeCategory | None:
        return db.query(SteelGradeCategory).filter(SteelGradeCategory.grade == grade).first()

    def list_by_grades(self, db: Session, grades: list[str]) -> list[SteelGradeCategory]:
        if not grades:
            return []
        return db.query(SteelGradeCategory).filter(SteelGradeCategory.grade.in_(grades)).all()

    def _build_list_query(
        self,
        db: Session,
        *,
        grade: str | None = None,
        category_name: str | None = None,
    ) -> Query[SteelGradeCategory]:
        query = db.query(SteelGradeCategory)
        if grade:
            query = query.filter(SteelGradeCategory.grade.like(f"%{grade}%"))
        if category_name:
            query = query.filter(SteelGradeCategory.category_name == category_name)
        return query

    def _ordered(self, query: Query[SteelGradeCategory]) -> Query[SteelGradeCategory]:
        return query.order_by(
            SteelGradeCategory.category_seq.asc(),
            SteelGradeCategory.grade.asc(),
        )

    def paginate(
        self,
        db: Session,
        *,
        grade: str | None = None,
        category_name: str | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[SteelGradeCategory], int]:
        query = self._build_list_query(
            db,
            grade=grade,
            category_name=category_name,
        )
        total = query.count()
        records = self._ordered(query).offset(skip).limit(limit).all()
        return records, total

    def list_for_export(
        self,
        db: Session,
        *,
        grade: str | None = None,
        category_name: str | None = None,
    ) -> list[SteelGradeCategory]:
        query = self._build_list_query(
            db,
            grade=grade,
            category_name=category_name,
        )
        return self._ordered(query).all()

    def list_grade_values(
        self,
        db: Session,
        *,
        category_name: str,
        grade: str | None = None,
    ) -> list[str]:
        query = db.query(SteelGradeCategory.grade).filter(
            SteelGradeCategory.category_name == category_name,
        )
        if grade:
            query = query.filter(SteelGradeCategory.grade.like(f"%{grade}%"))
        rows = query.order_by(SteelGradeCategory.grade.asc()).all()
        return [row[0] for row in rows]

    def create(self, db: Session, payload: SteelGradeCategoryInsert) -> SteelGradeCategory:
        record = model_from_payload(SteelGradeCategory, payload)
        db.add(record)
        db.flush()
        return record

    def apply_patch(
        self,
        db: Session,
        record: SteelGradeCategory,
        patch: SteelGradeCategoryPatch,
    ) -> SteelGradeCategory:
        apply_payload_fields(record, patch)
        db.flush()
        return record

    def delete(self, db: Session, record: SteelGradeCategory) -> None:
        db.delete(record)
        db.flush()
