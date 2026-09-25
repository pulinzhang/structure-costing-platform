"""删材料变更时挡住的结果表。只维护这一张。"""

from sqlalchemy.orm import Session

from app.models.settings.logical_ref.model import LogicalRef, LogicalRefFilter
from app.repositories.settings.logical_ref.repository import LogicalRefRepository

_DELETED = "stamping_part_material_changes"
_RESULT = "steel_prices"
_PART = "stamping_parts"


def rows() -> tuple[LogicalRef, list[LogicalRefFilter]]:
    head = LogicalRef(
        deleted_table=_DELETED,
        result_table=_RESULT,
        result_name="钢材联动价",
        hint="请到「核价 → 冲压钢材联动价 → 冲压钢材联动价一览」处理",
    )
    filters = [
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=1,
            compare="eq",
            result_column="grade",
            value_column="after_material",
        ),
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=2,
            compare="eq",
            result_column="location",
            value_table=_PART,
            value_column="location",
            join_from_column="part_id",
            join_to_column="id",
        ),
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=3,
            compare="eq",
            result_column="thickness",
            value_table=_PART,
            value_column="thickness",
            join_from_column="part_id",
            join_to_column="id",
        ),
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=4,
            compare="period_gte",
            result_year_column="year",
            result_month_column="month",
            value_column="effective_year",
            value_month_column="effective_month",
        ),
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=5,
            compare="period_before_next",
            result_year_column="year",
            result_month_column="month",
            value_column="effective_year",
            value_month_column="effective_month",
            next_table=_DELETED,
            next_mode="after",
            next_group_column="part_id",
            next_group_remote="part_id",
            next_year_column="effective_year",
            next_month_column="effective_month",
        ),
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=6,
            compare="period_gte",
            result_year_column="year",
            result_month_column="month",
            value_table=_PART,
            value_column="effective_year",
            value_month_column="effective_month",
            join_from_column="part_id",
            join_to_column="id",
        ),
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=7,
            compare="period_lte",
            result_year_column="year",
            result_month_column="month",
            value_table=_PART,
            value_column="expiry_year",
            value_month_column="expiry_month",
            join_from_column="part_id",
            join_to_column="id",
        ),
    ]
    return head, filters


def ensure(db: Session) -> None:
    head, filters = rows()
    LogicalRefRepository().insert_if_absent(db, head, filters)
    db.commit()
