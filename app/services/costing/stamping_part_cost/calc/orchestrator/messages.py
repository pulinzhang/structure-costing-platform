"""冲压零件核价过程文案（给人看，不写字段名）。"""

from __future__ import annotations

from decimal import Decimal

from app.common.period import format_period
from app.services.costing.stamping_part_cost.calc.constants import ALL_SUPPLIERS_LOCK
from app.services.costing.stamping_part_cost.calc.orchestrator.rates import PartCostCalcRates


def _number(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _percent(rate: Decimal) -> str:
    return f"{_number(rate * Decimal('100'))}%"


def format_prep_opening(year: int, month: int, location: str, vehicle_model: str) -> str:
    return f"开始计算：{format_period(year, month)}，{location}，{vehicle_model}，{ALL_SUPPLIERS_LOCK}。"


def format_rates(rates: PartCostCalcRates) -> str:
    return (
        f"这次用的费率：密度 {_number(rates.density)}，"
        f"材料损耗 {_percent(rates.loss_rate)}，"
        f"废料回收 {_percent(rates.recovery_rate)}，"
        f"财务 {_percent(rates.finance_rate)}，"
        f"管理 {_percent(rates.management_rate)}，"
        f"仓储包装 {_percent(rates.warehouse_packaging_rate)}，"
        f"税前利润 {_percent(rates.pretax_profit_rate)}。"
    )


def format_ready(
    part_count: int,
    steel_price_count: int,
    scrap_price_count: int,
    process_fee_count: int,
    die_fee_count: int,
    gauge_fee_count: int,
) -> str:
    return (
        f"核对过了：零件 {part_count} 个，钢材联动价 {steel_price_count} 条，"
        f"废料价 {scrap_price_count} 条，加工费 {process_fee_count} 条，"
        f"模具费 {die_fee_count} 条，检具费 {gauge_fee_count} 条。"
    )


def format_scrap_price(net_price: Decimal) -> str:
    return f"废料销售净价 {_number(net_price)} 元/吨。"


def format_parts_matched(part_count: int) -> str:
    return f"这个月要算的冲压零件 {part_count} 个。"


def format_missing_scrap(location: str, year: int, month: int) -> str:
    return f"{location} {format_period(year, month)}还没有废料销售价，请先维护废料月度价。"


def format_no_parts(location: str, vehicle_model: str, year: int, month: int) -> str:
    return f"{location} {vehicle_model} 在 {format_period(year, month)}没有有效期内的冲压零件。"


def format_persist_summary(success_count: int, failed_count: int, skipped_count: int) -> str:
    if failed_count and success_count:
        head = f"算完 {success_count} 个，还有 {failed_count} 个没算上"
    elif failed_count:
        head = f"{failed_count} 个都没算上"
    elif success_count:
        head = f"{success_count} 个零件都算完了"
    else:
        head = "没有写入零件价格"
    if skipped_count:
        return f"{head}。另有 {skipped_count} 个已经审核过，这次没重算。"
    if failed_count:
        return f"{head}，原因写在下面。"
    return f"{head}。"


def format_failed_part(part_number: str, reason: str) -> str:
    return f"没算上 {part_number}：{reason}"
