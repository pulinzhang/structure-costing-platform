"""钢价政策查询过滤条件。"""

from decimal import Decimal


class PolicyFilter:
    """政策查询过滤条件（封装分页参数）。"""

    def __init__(
        self,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
        policy_type: str | None = None,
        grade_type: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        self.year = year
        self.month = month
        self.steel_mill = steel_mill
        self.category_names_in = category_names_in
        self.category_filter_no_match = category_filter_no_match
        self.policy_type = policy_type
        self.grade_type = grade_type
        self.skip = skip
        self.limit = limit


class MatchFilter:
    """阶梯匹配查询过滤条件。"""

    def __init__(
        self,
        *,
        year: int,
        month: int,
        steel_mill: str,
        category_name: str,
        policy_type: str,
        grade_type: str | None = None,
        grade_value: str | None = None,
        base_thickness: Decimal | None = None,
    ):
        self.year = year
        self.month = month
        self.steel_mill = steel_mill
        self.category_name = category_name
        self.policy_type = policy_type
        self.grade_type = grade_type
        self.grade_value = grade_value
        self.base_thickness = base_thickness
