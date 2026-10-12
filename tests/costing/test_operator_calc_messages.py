from decimal import Decimal

from app.common.operator_copy import OPERATOR_CALC_INTERRUPTED, operator_failure_text
from app.exceptions.base import BusinessException
from app.services.costing.stamping_part_cost.calc.orchestrator.messages import (
    format_persist_summary,
    format_prep_opening,
    format_rates,
    format_scrap_price,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.rates import PartCostCalcRates
from app.services.costing.steel_price.calc.orchestrator.messages import (
    format_base_hits,
    format_missing_grade,
    format_prep_opening as format_steel_opening,
    format_saved,
    format_thickness,
)


def test_part_cost_report_has_no_field_names() -> None:
    rates = PartCostCalcRates(
        density=Decimal("7.85"),
        loss_rate=Decimal("0.003"),
        recovery_rate=Decimal("0.97"),
        finance_rate=Decimal("0.02"),
        management_rate=Decimal("0.02"),
        warehouse_packaging_rate=Decimal("0.01"),
        pretax_profit_rate=Decimal("0.05"),
        swing_shear_fee_per_ton=Decimal("0"),
    )
    text = "\n".join(
        [
            format_prep_opening(2026, 1, "芜湖", "T13J"),
            format_rates(rates),
            format_scrap_price(Decimal("1850.5")),
            format_persist_summary(40, 0, 2),
        ]
    )
    assert "开始计算：2026年01月，芜湖，T13J，全部工厂。" in text
    assert "材料损耗 0.3%" in text
    assert "废料销售净价 1850.5 元/吨。" in text
    assert "另有 2 个已经审核过" in text
    assert "year=" not in text
    assert "id=" not in text
    assert "formula" not in text


def test_steel_price_report_has_no_step_codes() -> None:
    text = "\n".join(
        [
            format_steel_opening(2026, 1, "芜湖"),
            format_base_hits(40, 2),
            *format_thickness(30, 5, 0, ["宝钢"]),
            format_saved(10, 0, 3, 0),
            format_missing_grade("芜湖", "DC04", "冷轧"),
        ]
    )
    assert "开始计算：2026年01月，芜湖。" in text
    assert "Step" not in text
    assert "match_status" not in text
    assert "id=" not in text
    assert "已经审核过" in text
    assert "芜湖 的 DC04（冷轧）在基价表里没有这个牌号。" in text


def test_failure_text_keeps_business_sentence() -> None:
    refusal = BusinessException("芜湖 T13J 在 2026年07月没有有效期内的材料清单")
    assert operator_failure_text(refusal) == refusal.message
    assert "IntegrityError" not in operator_failure_text(RuntimeError("IntegrityError: fk"))
    assert operator_failure_text(RuntimeError("IntegrityError: fk")) == OPERATOR_CALC_INTERRUPTED
