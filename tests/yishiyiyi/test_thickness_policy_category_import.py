"""厚度政策：期货生效期解析 + 大类 CATEGORY 解析。"""

from __future__ import annotations

from pathlib import Path

from app.common.policy_effective_period import (
    effective_period_from_policy_filename,
    effective_periods_from_directory_name,
    effective_periods_from_policy_filename,
    effective_periods_from_sample_path,
)
from app.parsers.yishiyiyi.policy.models.policy import GRADE_TYPE_CATEGORY


def test_effective_period_from_sample_filename() -> None:
    name = "外协钢板2026年1月订单（2026年2月 冲焊件原料）一事一议价格厚度加减价.xlsx"
    period = effective_period_from_policy_filename(name)
    assert period is not None
    assert period.year == 2026
    assert period.month == 2


def test_effective_period_short_year_in_paren() -> None:
    name = "24年6月订单（24年7月原料）钢厂厚度加减价-奇瑞发布2405.xls"
    period = effective_period_from_policy_filename(name)
    assert period is not None
    assert period.year == 2024
    assert period.month == 7


def test_effective_periods_dual_months_in_paren() -> None:
    name = "外协钢板2025年5月和6月订单（2025年6月和7月冲焊件原料）一事一议价格厚度加减价.xlsx"
    periods = effective_periods_from_policy_filename(name)
    assert [(p.year, p.month) for p in periods] == [(2025, 6), (2025, 7)]


def test_effective_period_from_directory_name() -> None:
    assert [
        (p.year, p.month)
        for p in effective_periods_from_directory_name("25年9月订单10月冲焊件及废料价格")
    ] == [(2025, 10)]
    assert [
        (p.year, p.month)
        for p in effective_periods_from_directory_name("25年12月订26年1月冲焊件及废料价格")
    ] == [(2026, 1)]
    assert [
        (p.year, p.month)
        for p in effective_periods_from_directory_name("26年1月订2月冲焊件及废料价格")
    ] == [(2026, 2)]


def test_directory_overrides_wrong_filename_paren() -> None:
    root = Path(__file__).resolve().parents[2] / "excel_sample" / "25年-26年一事一议价格"
    path = (
        root
        / "2025年1月-12月一事一议价格"
        / "25年9月订单10月冲焊件及废料价格"
        / "25年8月份订单（25年9月原料）发布价格及中标钢厂.xlsx"
    )
    periods = effective_periods_from_sample_path(path, root=root)
    assert [(p.year, p.month) for p in periods] == [(2025, 10)]


def test_parse_sample_thickness_policies_are_category_level() -> None:
    from app.parsers.yishiyiyi.policy.steel_price_policy_parser import (
        parse_steel_price_policy_excel,
    )

    sample_root = Path(__file__).resolve().parents[2] / "excel_sample" / "25年-26年一事一议价格"
    root = sample_root / "2026年1月-12月一事一议价格"
    files = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and "厚度加减价" in path.name and path.suffix.lower() == ".xlsx"
    ]
    if not files:
        return

    sample = files[0]
    periods = effective_periods_from_sample_path(sample, root=sample_root)
    assert periods
    period = periods[0]
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
