"""单零件价格核算（材料消耗 / 废料扣除 / 加工费合计）。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.swing_shear import applied_swing_shear_fee_per_ton, steel_kg_price_with_swing_shear
from app.models.stamping import StampingPart
from app.models.yishiyiyi import StampingScrapPrice
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostCalcAmounts,
    StampingPartCostPartSnapshot,
)
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostFailedItemVO
from app.services.costing.stamping_part_cost.calc.constants import (
    AMOUNT_QUANTIZE,
    UTIL_QUANTIZE,
    compute_finished_cost_stack,
    quantize,
)
from app.services.costing.stamping_part_cost.calc.fees.die import DieFeeResolver
from app.services.costing.stamping_part_cost.calc.fees.gauge import GaugeFeeResolver
from app.services.costing.stamping_part_cost.calc.fees.process import ProcessFeeResolver
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.stamping_part_cost.helpers import to_decimal


def part_snapshot(part: StampingPart) -> StampingPartCostPartSnapshot:
    """零件主表 → 当月核价结果快照。

    是否利废、利用哪类废料必须写进结果表（年+月唯一键），不能只活在零件主表：
    这个月废料够用按利废算，下月废料不足改零件后再算下月，本月行保持原快照。
    """
    return StampingPartCostPartSnapshot(
        source_part_id=part.id,
        seq_no=part.seq_no,
        part_number=part.part_number,
        part_name=part.part_name,
        material=part.material,
        thickness=part.thickness,
        part_weight=part.part_weight,
        sheet_length=part.sheet_length,
        sheet_width=part.sheet_width,
        parts_per_sheet=part.parts_per_sheet,
        sheet_type=part.sheet_type,
        is_offal_nested=bool(part.is_offal_nested),
        offal_source=part.offal_source,
        has_swing_shear=bool(part.has_swing_shear),
        die_type=part.die_type,
        process_method=part.process_method,
        automation=part.automation,
        part_remark=part.remark,
        sketch_url=part.sketch_url,
        excel_filename=part.excel_filename,
        excel_sheet_name=part.excel_sheet_name,
        excel_row=part.excel_row,
        excel_part_col=part.excel_part_col,
    )


class PartCostCalculator:
    """按奇瑞核价口径计算单件材料净成本与最终单价。"""

    def __init__(
        self,
        price_resolver: PriceResolver | None = None,
        process_fee_resolver: ProcessFeeResolver | None = None,
        die_fee_resolver: DieFeeResolver | None = None,
        gauge_fee_resolver: GaugeFeeResolver | None = None,
    ) -> None:
        self.price_resolver = price_resolver or PriceResolver()
        self.process_fee_resolver = process_fee_resolver or ProcessFeeResolver()
        self.die_fee_resolver = die_fee_resolver or DieFeeResolver()
        self.gauge_fee_resolver = gauge_fee_resolver or GaugeFeeResolver()

    def calc_part_cost(
        self,
        db: Session,
        *,
        part: StampingPart,
        year: int,
        month: int,
        supplier: str,
        scrap: StampingScrapPrice,
        scrap_ton_price: Decimal,
        density: Decimal,
        loss_rate: Decimal,
        recovery_rate: Decimal,
        finance_rate: Decimal,
        management_rate: Decimal,
        warehouse_packaging_rate: Decimal,
        pretax_profit_rate: Decimal,
        swing_shear_fee_per_ton: Decimal = Decimal("0"),
    ) -> StampingPartCostCalcAmounts | StampingPartCostFailedItemVO:
        material = (part.material or "").strip()
        is_offal_nested = bool(part.is_offal_nested)
        if not is_offal_nested and not material:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="材质为空，无法匹配钢材联动价",
            )

        sheet_length = to_decimal(part.sheet_length)
        sheet_width = to_decimal(part.sheet_width)
        thickness = to_decimal(part.thickness)
        part_weight = to_decimal(part.part_weight)
        parts_per_sheet = part.parts_per_sheet
        kg_scale = Decimal("1000")
        scrap_kg_price = scrap_ton_price / kg_scale
        applied_swing_fee = applied_swing_shear_fee_per_ton(
            has_swing_shear=bool(part.has_swing_shear),
            fee_per_ton=swing_shear_fee_per_ton,
        )

        if is_offal_nested:
            if part_weight is None or part_weight <= 0:
                return StampingPartCostFailedItemVO(
                    part_number=part.part_number,
                    part_name=part.part_name,
                    reason="利废件须有成品净重",
                )
            finished_total_kg = part_weight
            blank_kg = part_weight
            scrap_kg = Decimal("0")
            utilization = quantize(Decimal("100"), UTIL_QUANTIZE)
            steel_ton_price = scrap_ton_price
            steel_price_id = None
            steel_mill = None
            material_amount_sheet = quantize(part_weight * scrap_kg_price, AMOUNT_QUANTIZE)
            loss_scrap_deduction = quantize(Decimal("0"), AMOUNT_QUANTIZE)
            process_scrap_deduction = quantize(Decimal("0"), AMOUNT_QUANTIZE)
            scrap_amount_sheet = quantize(Decimal("0"), AMOUNT_QUANTIZE)
            material_net_per_part = material_amount_sheet
        else:
            if (
                sheet_length is None
                or sheet_width is None
                or thickness is None
                or part_weight is None
                or parts_per_sheet is None
            ):
                return StampingPartCostFailedItemVO(
                    part_number=part.part_number,
                    part_name=part.part_name,
                    reason="料片尺寸/料厚/单重/可制件数不完整",
                )
            if parts_per_sheet <= 0:
                return StampingPartCostFailedItemVO(
                    part_number=part.part_number,
                    part_name=part.part_name,
                    reason="可制件数必须大于 0",
                )

            blank_kg = (
                (sheet_length * sheet_width * thickness * density)
                / Decimal("1000000")
                / Decimal(parts_per_sheet)
            )
            if blank_kg <= 0:
                return StampingPartCostFailedItemVO(
                    part_number=part.part_number,
                    part_name=part.part_name,
                    reason="预估单件材料消耗计算结果无效",
                )

            finished_total_kg = part_weight
            scrap_kg = blank_kg - finished_total_kg
            utilization = quantize((finished_total_kg / blank_kg) * Decimal("100"), UTIL_QUANTIZE)

            steel_rows = self.price_resolver.find_steel_prices(
                db,
                year=year,
                month=month,
                location=part.location,
                grade=material,
                thickness=thickness,
            )
            steel = self.price_resolver.pick_steel_price(steel_rows)
            if steel is None:
                return StampingPartCostFailedItemVO(
                    part_number=part.part_number,
                    part_name=part.part_name,
                    reason=f"未匹配到钢材联动价（材质={material}, 料厚={thickness}）",
                )
            steel_ton_price = Decimal(str(steel.final_price_per_ton))
            steel_price_id = steel.id
            steel_mill = steel.steel_mill
            steel_kg_price = steel_kg_price_with_swing_shear(steel_ton_price, applied_swing_fee)
            material_amount_sheet = quantize(
                blank_kg * steel_kg_price * (Decimal("1") + loss_rate),
                AMOUNT_QUANTIZE,
            )
            loss_scrap_deduction = quantize(
                blank_kg * loss_rate * recovery_rate * scrap_kg_price,
                AMOUNT_QUANTIZE,
            )
            process_scrap_deduction = quantize(
                scrap_kg * recovery_rate * scrap_kg_price,
                AMOUNT_QUANTIZE,
            )
            scrap_amount_sheet = quantize(
                loss_scrap_deduction + process_scrap_deduction,
                AMOUNT_QUANTIZE,
            )
            material_net_per_part = quantize(
                material_amount_sheet - loss_scrap_deduction - process_scrap_deduction,
                AMOUNT_QUANTIZE,
            )

        process = self.process_fee_resolver.lookup(db, part=part, year=year, supplier=supplier)
        if isinstance(process, StampingPartCostFailedItemVO):
            return process
        die = self.die_fee_resolver.lookup(
            db,
            year=year,
            location=part.location,
            vehicle_model=part.vehicle_model,
            part_number=part.part_number,
        )
        gauge = self.gauge_fee_resolver.lookup(
            db,
            location=part.location,
            vehicle_model=part.vehicle_model,
            part_number=part.part_number,
        )

        (
            direct_cost,
            finished_finance_fee,
            finished_management_fee,
            finished_warehouse_packaging_fee,
            finished_pretax_profit_fee,
            unit_cost,
        ) = compute_finished_cost_stack(
            material_net_per_part=material_net_per_part,
            process_fee_amount=process.process_fee_amount,
            die_fee_amount=die.die_fee_amount,
            gauge_fee_amount=gauge.gauge_fee_amount,
            finance_rate=finance_rate,
            management_rate=management_rate,
            warehouse_packaging_rate=warehouse_packaging_rate,
            pretax_profit_rate=pretax_profit_rate,
        )

        return StampingPartCostCalcAmounts(
            density=density,
            material_loss_rate=loss_rate,
            scrap_recovery_rate=recovery_rate,
            blank_weight_kg=blank_kg,
            finished_total_kg=finished_total_kg,
            scrap_weight_kg=scrap_kg,
            material_utilization_pct=utilization,
            steel_price_id=steel_price_id,
            steel_mill=steel_mill,
            steel_ton_price=steel_ton_price,
            swing_shear_fee_per_ton=applied_swing_fee,
            scrap_price_id=scrap.id,
            scrap_ton_price=scrap_ton_price,
            process_fee_id=process.process_fee_id,
            process_fee_amount=process.process_fee_amount,
            die_fee_id=die.die_fee_id,
            die_fee_amount=die.die_fee_amount,
            gauge_fee_id=gauge.gauge_fee_id,
            gauge_fee_amount=gauge.gauge_fee_amount,
            material_amount_sheet=material_amount_sheet,
            loss_scrap_deduction=loss_scrap_deduction,
            process_scrap_deduction=process_scrap_deduction,
            scrap_amount_sheet=scrap_amount_sheet,
            material_net_per_part=material_net_per_part,
            direct_cost=direct_cost,
            finished_finance_fee=finished_finance_fee,
            finished_management_fee=finished_management_fee,
            finished_warehouse_packaging_fee=finished_warehouse_packaging_fee,
            finished_pretax_profit_fee=finished_pretax_profit_fee,
            unit_cost=unit_cost,
        )
