"""导出筛选：至少选一个条件后再出 Excel；采购册须锁期别范围；一事一议须锁年月。"""

from app.exceptions.base import BusinessException


def require_at_least_one_export_filter(*values: object) -> None:
    if not any(values):
        raise BusinessException("请至少选择一个筛选条件后再导出")


def require_year_month_export_filters(year: object, month: object) -> None:
    """一事一议按月定价：导出须锁年度 + 月份。"""
    if not year or not month:
        raise BusinessException("导出须选定年度和月份（一事一议按月定价）")


def require_period_scope_export_filters(
    year: object,
    month: object,
    location: object,
    vehicle_model: object,
) -> None:
    """采购导出须锁年/月/基地/项目；版本可选（同月可多工程变更字）。"""
    if not all((year, month, location, vehicle_model)):
        raise BusinessException("采购导出须选定年度、月份、基地、项目（版本可不选）")
