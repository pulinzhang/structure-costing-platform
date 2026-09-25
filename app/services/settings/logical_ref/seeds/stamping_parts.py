"""删冲压零件时挡住的结果表。只维护这一张。"""

from app.models.settings.logical_ref.model import LogicalRef, LogicalRefFilter

_DELETED = "stamping_parts"
_RESULT = "steel_prices"
_CHANGE = "stamping_part_material_changes"


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
            result_column="location",
            value_column="location",
        ),
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=2,
            compare="eq",
            result_column="grade",
            value_column="material",
        ),
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=3,
            compare="eq",
            result_column="thickness",
            value_column="thickness",
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
            compare="period_lte",
            result_year_column="year",
            result_month_column="month",
            value_column="expiry_year",
            value_month_column="expiry_month",
        ),
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=6,
            compare="period_before_next",
            result_year_column="year",
            result_month_column="month",
            next_table=_CHANGE,
            next_mode="first",
            next_group_column="id",
            next_group_remote="part_id",
            next_year_column="effective_year",
            next_month_column="effective_month",
            skip_when="is_tailor_welded,is_offal_nested,is_scrap_byproduct",
        ),
    ]
    return head, filters
