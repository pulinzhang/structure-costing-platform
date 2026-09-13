"""缺价判定（grand_total 空或 ≤0）。"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.models.costing.assembly_cost import AssemblyCost


def is_missing_price() -> ColumnElement[bool]:
    return or_(
        AssemblyCost.grand_total.is_(None),
        AssemblyCost.grand_total <= 0,
    )
