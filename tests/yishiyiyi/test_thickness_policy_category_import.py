"""厚度政策：期货生效期解析 + 大类 CATEGORY 解析。"""

from __future__ import annotations

from app.common.policy_effective_period import effective_period_from_policy_filename
from app.parsers.yishiyiyi.policy.models.policy import GRADE_TYPE_CATEGORY


def test_effective_period_from_sample_filename() -> None:
    name = "外协钢板2026年1月订单（2026年2月 冲焊件原料）一事一议价格厚度加减价.xlsx"
    period = effective_period_from_policy_filename(name)
    assert period is not None
    assert period.year == 2026
    assert period.month == 2


def test_parse_sample_thickness_policies_are_category_level() -> None:
    from pathlib import Path

    from app.parsers.yishiyiyi.policy import parse_steel_price_policy_excel

    root = (
        Path(__file__).resolve().parents[1]
        / "excel_sample"
        / "25年-26年一事一议价格"
        / "2026年1月-12月一事一议价格"
    )
    files = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and "厚度加减价" in path.name and path.suffix.lower() == ".xlsx"
    ]
    if not files:
        return

    sample = files[0]
    period = effective_period_from_policy_filename(sample.name)
    assert period is not None
    content = sample.read_bytes()
    result = parse_steel_price_policy_excel(
        content,
        year=period.year,
        month=period.month,
        excel_filename=sample.name,
    )
    assert result.policies, "样例应解析出至少一条政策"
    assert all(policy.policy_type == "THICKNESS" for policy in result.policies)
    assert all(policy.policy_type != "WIDTH" for policy in result.policies)
    assert all(policy.grade_type == GRADE_TYPE_CATEGORY for policy in result.policies)
    assert all(policy.grade_value == policy.category_name for policy in result.policies)
