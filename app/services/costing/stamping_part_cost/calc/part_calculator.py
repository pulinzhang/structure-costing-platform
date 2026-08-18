"""单零件价格核算（材料消耗 / 废料扣除 / 加工费合计）。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.stamping import StampingPart
from app.models.yishiyiyi import StampingScrapPrice
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostCalcAmounts,
    StampingPartCostPartSnapshot,
)
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostFailedItemVO
from app.services.costing.stamping_part_cost.calc.constants import (
    AMOUNT_QUANTIZE,
    FEE_QUANTIZE,
    UTIL_QUANTIZE,
    quantize,
)
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.stamping_part_cost.helpers import to_decimal


def part_snapshot(part: StampingPart) -> StampingPartCostPartSnapshot:
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
        fee_repo: StampingProcessFeeRepository | None = None,
    ) -> None:
        self.price_resolver = price_resolver or PriceResolver()
        self.fee_repo = fee_repo or StampingProcessFeeRepository()

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
    ) -> StampingPartCostCalcAmounts | StampingPartCostFailedItemVO:
        material = (part.material or "").strip()
        if not material:
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

        # 对齐 Excel M：L×W×T×density/1e6/可制件数（不做中间四舍五入）
        blank_kg = (
            sheet_length * sheet_width * thickness * density
        ) / Decimal("1000000") / Decimal(parts_per_sheet)
        if blank_kg <= 0:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="预估单件材料消耗计算结果无效",
            )

        # Excel：O=M−H，N=H/M；finished 存净重 H
        finished_total_kg = part_weight
        scrap_kg = blank_kg - finished_total_kg
        utilization = quantize(
            (finished_total_kg / blank_kg) * Decimal("100"), UTIL_QUANTIZE
        )

        steel_rows = self.price_resolver.find_steel_prices(
            db,
            year=year,
            month=month,
            location=part.location,
            grade=material,
            thickness=thickness,
        )
        if not steel_rows:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason=f"未匹配到钢材联动价（材质={material}, 料厚={thickness}）",
            )
        if len(steel_rows) > 1:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason=(
                    f"钢材联动价匹配到 {len(steel_rows)} 条，"
                    "中标场景应唯一，请检查数据"
                ),
            )
        steel = steel_rows[0]
        steel_ton_price = Decimal(str(steel.final_price_per_ton))

        fee = self.fee_repo.get_by_business_key(
            db,
            year=year,
            location=part.location,
            stamping_supplier=supplier,
            vehicle_model=part.vehicle_model,
            version=part.version,
            part_number=part.part_number,
        )
        if fee is None:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="未找到对应加工费结果",
            )
        if fee.final_processing_fee is None:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="加工费最终金额为空，请先完成加工费计算或手工调整",
            )
        process_fee_amount = quantize(
            Decimal(str(fee.final_processing_fee)), FEE_QUANTIZE
        )

        # 对齐 Excel R 三项分列：
        # ① M×P×(1+λ)  ② M×λ×η×Q  ③ O×η×Q   （P/Q=元/kg=吨价/1000）
        kg_scale = Decimal("1000")
        steel_kg_price = steel_ton_price / kg_scale
        scrap_kg_price = scrap_ton_price / kg_scale
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
        unit_cost = quantize(
            material_net_per_part + process_fee_amount, AMOUNT_QUANTIZE
        )

        return StampingPartCostCalcAmounts(
            density=density,
            material_loss_rate=loss_rate,
            scrap_recovery_rate=recovery_rate,
            blank_weight_kg=blank_kg,
            finished_total_kg=finished_total_kg,
            scrap_weight_kg=scrap_kg,
            material_utilization_pct=utilization,
            steel_price_id=steel.id,
            steel_mill=steel.steel_mill,
            steel_ton_price=steel_ton_price,
            scrap_price_id=scrap.id,
            scrap_ton_price=scrap_ton_price,
            process_fee_id=fee.id,
            process_fee_amount=process_fee_amount,
            material_amount_sheet=material_amount_sheet,
            loss_scrap_deduction=loss_scrap_deduction,
            process_scrap_deduction=process_scrap_deduction,
            scrap_amount_sheet=scrap_amount_sheet,
            material_net_per_part=material_net_per_part,
            unit_cost=unit_cost,
        )
