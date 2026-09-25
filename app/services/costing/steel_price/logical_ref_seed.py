"""删钢材联动价时挡住的结果表。只维护这一张。"""

from sqlalchemy.orm import Session

from app.models.settings.logical_ref.model import LogicalRef, LogicalRefFilter
from app.repositories.settings.logical_ref.repository import LogicalRefRepository

_DELETED = "steel_prices"
_RESULT = "stamping_part_costs"


def rows() -> tuple[LogicalRef, list[LogicalRefFilter]]:
    head = LogicalRef(
        deleted_table=_DELETED,
        result_table=_RESULT,
        result_name="冲压零件价格",
        hint="请到「核价 → 冲压零件价格核算 → 冲压零件价格一览」处理",
    )
    filters = [
        LogicalRefFilter(
            deleted_table=_DELETED,
            result_table=_RESULT,
            seq=1,
            compare="eq",
            result_column="steel_price_id",
            value_column="id",
        ),
    ]
    return head, filters


def ensure(db: Session) -> None:
    head, filters = rows()
    LogicalRefRepository().insert_if_absent(db, head, filters)
    db.commit()
