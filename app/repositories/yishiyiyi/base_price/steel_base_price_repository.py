"""
钢材基准价格 Repository
只负责数据库访问，事务由 Service 层管理
"""

from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import distinct, func
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.common.types.repository_types import SteelBasePriceFilterOptions
from app.models.yishiyiyi import SteelBasePrice
from app.repositories.persist import apply_dto_fields, apply_payload_fields, model_from_payload
from app.schemas.dto.steel_base_price_dto import (
    BasePriceUpsertCounts,
    SteelBasePriceCreate,
    SteelBasePriceUpdate,
    SteelBasePriceWrite,
)

TValue = TypeVar("TValue")

_UPSERT_UPDATE_SKIP = frozenset(
    {
        "id",
        "year",
        "month",
        "location",
        "steel_mill",
        "category_name",
        "grade",
        "thick",
        "width",
        "spec",
        "created_by",
        "created_at",
        "updated_at",
    }
)


class BasePriceFilter:
    """基准价格查询过滤条件（封装分页参数）。"""

    def __init__(
        self,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        spec: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        self.year = year
        self.month = month
        self.location = location
        self.locations = locations
        self.steel_mill = steel_mill
        self.category_name = category_name
        self.grade = grade
        self.spec = spec
        self.skip = skip
        self.limit = limit


class SteelBasePriceRepository:
    """钢材基准价格数据访问。"""

    # ---- 查询 ----

    def get_by_id(self, db: Session, record_id: int) -> SteelBasePrice | None:
        """根据主键查询单条记录。"""
        return db.query(SteelBasePrice).filter(SteelBasePrice.id == record_id).first()

    def paginate(
        self,
        db: Session,
        base_price_filter: BasePriceFilter,
    ) -> tuple[list[SteelBasePrice], int]:
        """分页筛选基准价格。"""
        query = db.query(SteelBasePrice)

        if base_price_filter.year is not None:
            query = query.filter(SteelBasePrice.year == base_price_filter.year)
        if base_price_filter.month is not None:
            query = query.filter(SteelBasePrice.month == base_price_filter.month)
        if base_price_filter.locations is not None:
            query = query.filter(SteelBasePrice.location.in_(base_price_filter.locations))
        elif base_price_filter.location:
            query = query.filter(SteelBasePrice.location == base_price_filter.location)
        if base_price_filter.steel_mill:
            query = query.filter(SteelBasePrice.steel_mill == base_price_filter.steel_mill)
        if base_price_filter.category_name:
            query = query.filter(SteelBasePrice.category_name == base_price_filter.category_name)
        if base_price_filter.grade:
            query = query.filter(SteelBasePrice.grade.contains(base_price_filter.grade))
        if base_price_filter.spec:
            query = query.filter(SteelBasePrice.spec.contains(base_price_filter.spec))

        total = query.count()
        records = (
            query.order_by(
                SteelBasePrice.year.asc(),
                SteelBasePrice.month.asc(),
                SteelBasePrice.location.asc(),
                SteelBasePrice.steel_mill.asc(),
                SteelBasePrice.excel_col.asc(),
                SteelBasePrice.excel_row.asc(),
            )
            .offset(base_price_filter.skip)
            .limit(base_price_filter.limit)
            .all()
        )
        return records, total

    def list_distinct_grade_categories(self, db: Session) -> list[tuple[str, str]]:
        """全表去重 (grade, category_name)，供牌号档案回填。"""
        rows = (
            db.query(SteelBasePrice.grade, SteelBasePrice.category_name)
            .filter(SteelBasePrice.grade.isnot(None))
            .distinct()
            .all()
        )
        result: list[tuple[str, str]] = []
        for grade, category_name in rows:
            grade_text = (grade or "").strip()
            category_text = (category_name or "").strip()
            if grade_text and category_text:
                result.append((grade_text, category_text))
        return result

    def map_most_frequent_category_by_grades(
        self, db: Session, grades: list[str]
    ) -> dict[str, str]:
        """牌号 → 基价行出现次数最多的大类。"""
        if not grades:
            return {}
        rows = (
            db.query(
                SteelBasePrice.grade,
                SteelBasePrice.category_name,
                func.count().label("hit_count"),
            )
            .filter(SteelBasePrice.grade.in_(grades))
            .group_by(SteelBasePrice.grade, SteelBasePrice.category_name)
            .all()
        )
        best: dict[str, tuple[str, int]] = {}
        for grade, category_name, hit_count in rows:
            grade_text = (grade or "").strip()
            category_text = (category_name or "").strip()
            if not grade_text or not category_text:
                continue
            previous = best.get(grade_text)
            count = int(hit_count)
            if previous is None or count > previous[1]:
                best[grade_text] = (category_text, count)
        return {grade: pair[0] for grade, pair in best.items()}

    # ---- 筛选选项 ----

    def _distinct_values(
        self,
        db: Session,
        column: InstrumentedAttribute[TValue],
        *,
        filter_none: bool = False,
        descending: bool = False,
    ) -> list[TValue]:
        """通用 distinct 值查询。"""
        query = db.query(distinct(column))
        if filter_none:
            query = query.filter(column.isnot(None))
        order_col = column.desc() if descending else column.asc()
        return [r[0] for r in query.order_by(order_col).all()]

    def get_filter_options(self, db: Session) -> SteelBasePriceFilterOptions:
        """返回各字段的筛选下拉选项。"""
        years = self._distinct_values(db, SteelBasePrice.year, descending=True)
        months = self._distinct_values(db, SteelBasePrice.month)
        locations = self._distinct_values(db, SteelBasePrice.location)
        steel_mills = self._distinct_values(db, SteelBasePrice.steel_mill)
        category_names = self._distinct_values(db, SteelBasePrice.category_name)
        grades = self._distinct_values(db, SteelBasePrice.grade)
        specs = self._distinct_values(db, SteelBasePrice.spec)
        return {
            "years": years,
            "months": months,
            "locations": locations,
            "steel_mills": steel_mills,
            "category_names": category_names,
            "grades": grades,
            "specs": specs,
        }

    def get_distinct_months_for_year(self, db: Session, year: int) -> list[int]:
        results = (
            db.query(SteelBasePrice.month)
            .filter(SteelBasePrice.year == year)
            .distinct()
            .order_by(SteelBasePrice.month)
            .all()
        )
        return [int(r[0]) for r in results if r[0] is not None]

    # ---- 写操作 ----

    def create(
        self,
        db: Session,
        data: SteelBasePriceCreate,
        *,
        created_by: str,
        updated_by: str,
    ) -> SteelBasePrice:
        """创建基准价格记录。"""
        record = model_from_payload(SteelBasePrice, data)
        record.created_by = created_by
        record.updated_by = updated_by
        db.add(record)
        return record

    def update(
        self,
        db: Session,
        record_id: int,
        update_data: SteelBasePriceUpdate,
        *,
        updated_by: str,
    ) -> SteelBasePrice | None:
        """按主键更新记录，返回更新后记录或 None（不存在）。"""
        record = self.get_by_id(db, record_id)
        if record is None:
            return None
        apply_dto_fields(record, update_data)
        record.updated_by = updated_by
        return record

    def delete(self, db: Session, record_id: int) -> bool:
        """按主键删除记录。"""
        record = self.get_by_id(db, record_id)
        if record is None:
            return False
        db.delete(record)
        return True

    # ---- Upsert ----

    def upsert(
        self,
        db: Session,
        records: list[SteelBasePriceWrite],
    ) -> BasePriceUpsertCounts:
        """
        按复合唯一键 (year, month, location, steel_mill, category_name, grade, thick, width)
        执行插入或更新。

        返回 ``{"created": 新增条数, "updated": 更新条数}``。
        """
        if not records:
            return {"created": 0, "updated": 0}

        created_count = 0
        updated_count = 0

        for record_data in records:
            existing = (
                db.query(SteelBasePrice)
                .filter(
                    SteelBasePrice.year == record_data.year,
                    SteelBasePrice.month == record_data.month,
                    SteelBasePrice.location == record_data.location,
                    SteelBasePrice.steel_mill == record_data.steel_mill,
                    SteelBasePrice.category_name == record_data.category_name,
                    SteelBasePrice.grade == record_data.grade,
                    SteelBasePrice.thick == record_data.thick,
                    SteelBasePrice.width == record_data.width,
                )
                .first()
            )
            if existing is not None:
                # 更新可变更字段（含修改人；创建人仅 insert 时写入）
                apply_payload_fields(existing, record_data, skip=_UPSERT_UPDATE_SKIP)
                updated_count += 1
            else:
                db.add(model_from_payload(SteelBasePrice, record_data))
                created_count += 1

        return {"created": created_count, "updated": updated_count}

    # ---- 条件批量删除 ----

    def delete_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        steel_mill: str | None = None,
    ) -> int:
        """
        根据条件批量删除记录。
        注意：此方法不 flush，由调用方（Service）控制事务。
        返回被删除的记录数量。
        """
        query = db.query(SteelBasePrice)

        if year is not None:
            query = query.filter(SteelBasePrice.year == year)
        if month is not None:
            query = query.filter(SteelBasePrice.month == month)
        if location:
            query = query.filter(SteelBasePrice.location == location)
        if steel_mill:
            query = query.filter(SteelBasePrice.steel_mill == steel_mill)

        count = query.count()
        query.delete(synchronize_session=False)
        return count

    # ---- 导出查询 ----

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        spec: str | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> list[SteelBasePrice]:
        """获取导出所需的数据（供 ExportService 调用），支持分页。"""
        query = db.query(SteelBasePrice)

        if year is not None:
            query = query.filter(SteelBasePrice.year == year)
        if month is not None:
            query = query.filter(SteelBasePrice.month == month)
        if locations is not None:
            if not locations:
                return []
            query = query.filter(SteelBasePrice.location.in_(locations))
        elif location:
            query = query.filter(SteelBasePrice.location == location)
        if steel_mill:
            query = query.filter(SteelBasePrice.steel_mill == steel_mill)
        if category_name:
            query = query.filter(SteelBasePrice.category_name == category_name)
        if grade:
            query = query.filter(SteelBasePrice.grade.contains(grade))
        if spec:
            query = query.filter(SteelBasePrice.spec.contains(spec))

        query = query.order_by(
            SteelBasePrice.year.asc(),
            SteelBasePrice.month.asc(),
            SteelBasePrice.location.asc(),
            SteelBasePrice.steel_mill.asc(),
            SteelBasePrice.excel_col.asc(),
            SteelBasePrice.excel_row.asc(),
        )

        if skip is not None:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        spec: str | None = None,
        grades_in: Sequence[str] | None = None,
    ) -> int:
        """统计导出数据总量。"""
        grade_list: list[str] | None = None
        if grades_in is not None:
            grade_list = [item for item in grades_in if item]
            if not grade_list:
                return 0
        query = db.query(func.count(SteelBasePrice.id))

        if year is not None:
            query = query.filter(SteelBasePrice.year == year)
        if month is not None:
            query = query.filter(SteelBasePrice.month == month)
        if location:
            query = query.filter(SteelBasePrice.location == location)
        if steel_mill:
            query = query.filter(SteelBasePrice.steel_mill == steel_mill)
        if category_name:
            query = query.filter(SteelBasePrice.category_name == category_name)
        if grade:
            query = query.filter(SteelBasePrice.grade.contains(grade))
        if spec:
            query = query.filter(SteelBasePrice.spec.contains(spec))
        if grade_list is not None:
            query = query.filter(SteelBasePrice.grade.in_(grade_list))

        return query.scalar() or 0
