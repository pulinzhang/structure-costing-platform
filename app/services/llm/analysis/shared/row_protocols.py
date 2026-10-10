"""LLM 分析用行协议（替代 duck-typed 入参）。

只描述「函数真正读到的字段」；具体 ORM/dataclass 行只要结构兼容即可。
属性用 @property 声明，以匹配 frozen dataclass 只读字段。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol


class HasAssemblyUnitPrice(Protocol):
    """assembly_unit_price：优先 should_cost，否则 total_amount。"""

    @property
    def should_cost(self) -> Decimal | None: ...

    @property
    def total_amount(self) -> Decimal | None: ...


class HasPeriodDiffAmounts(Protocol):
    """build_period_diff：首末月差分所需字段。"""

    @property
    def year(self) -> int: ...

    @property
    def month(self) -> int: ...

    @property
    def grand_total(self) -> Decimal | None: ...

    @property
    def stamping_amount(self) -> Decimal | None: ...

    @property
    def purchased_amount(self) -> Decimal | None: ...

    @property
    def bundle_amount(self) -> Decimal | None: ...

    @property
    def welding_amount(self) -> Decimal | None: ...
