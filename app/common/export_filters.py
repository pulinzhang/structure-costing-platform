"""导出筛选：至少选一个条件后再出 Excel；采购册须锁期别范围。"""

from app.exceptions.base import BusinessException


def require_at_least_one_export_filter(*values: object) -> None:
    if not any(values):
        raise BusinessException("请至少选择一个筛选条件后再导出")


def require_period_scope_export_filters(
    year: object,
    month: object,
    location: object,
    vehicle_model: object,
    bom_version: object,
) -> None:
    if not all((year, month, location, vehicle_model, bom_version)):
        raise BusinessException("采购导出须选定年度、月份、基地、项目、版本")
