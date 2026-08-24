"""
钢材基准价格 Repository
只负责数据库访问，事务由 Service 层管理
"""

from typing import Optional, TypeVar

from sqlalchemy import distinct, func
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.models.yishiyiyi import SteelBasePrice
from app.repositories.persist import apply_dto_fields, apply_payload_fields, model_from_payload
from app.schemas.dto.steel_base_price_dto import (
    BasePriceUpsertCounts,
    FilterOptions,
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
        year: Optional[int] = None,
        month: Optional[int] = None,
        location: Optional[str] = None,
        steel_mill: Optional[str] = None,
        category_name: Optional[str] = None,
        grade: Optional[str] = None,
        spec: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ):
        self.year = year
        self.month = month
        self.location = location
        self.steel_mill = steel_mill
        self.category_name = category_name
        self.grade = grade
        self.spec = spec
        self.skip = skip
        self.limit = limit


class SteelBasePriceRepository:
    """钢材基准价格数据访问。"""

    # ---- 查询 ----

    def get_by_id(self, db: Session, record_id: int) -> Optional[SteelBasePrice]:
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
        if base_price_filter.location:
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

    def get_filter_options(self, db: Session) -> FilterOptions:
        """返回各字段的筛选下拉选项。"""
        years = self._distinct_values(db, SteelBasePrice.year, descending=True)
        months = self._distinct_values(db, SteelBasePrice.month)
        locations = self._distinct_values(db, SteelBasePrice.location)
        steel_mills = self._distinct_values(db, SteelBasePrice.steel_mill)
        category_names = self._distinct_values(db, SteelBasePrice.category_name)
        grades = self._distinct_values(db, SteelBasePrice.grade)
        specs = self._distinct_values(db, SteelBasePrice.spec)
        return FilterOptions(
            years=years,
            months=months,
            locations=locations,
            steel_mills=steel_mills,
            category_names=category_names,
            grades=grades,
            specs=specs,
        )

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
    ) -> Optional[SteelBasePrice]:
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
        year: Optional[int] = None,
        month: Optional[int] = None,
        location: Optional[str] = None,
        steel_mill: Optional[str] = None,
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
    ) -> int:
        """统计导出数据总量。"""
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

        return query.scalar() or 0