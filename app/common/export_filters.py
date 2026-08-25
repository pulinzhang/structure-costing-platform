"""导出筛选：至少选一个条件后再出 Excel。"""

from app.exceptions.base import BusinessException


def require_at_least_one_export_filter(*values: object) -> None:
    if not any(values):
        raise BusinessException("请至少选择一个筛选条件后再导出")
