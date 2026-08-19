"""拼焊件零件价格核算。

预估单件材料消耗 M = Σ 各子片消耗（各片 L×W×T×密度/1e6/可制件数）。
成品净重 H = 父件 part_weight（焊后总成净重）。
废料 O = M − H。

各子片按自身材质/料厚匹配钢材联动价，各自算①②后金额相加；
③边角废料扣除按总成 O 一次计算。
落库吨价 P：单片（或各片同价）用该价；多片不同价时按子片消耗量加权，
使 M×P×(1+λ) 与分片合计一致。列表 VO 再按子片用 / 展示料厚、长、宽、吨价。
加工费取父件已算结果一行（不 × 片数）；拼焊费仍手工挂父，本层不加。
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.money import Q4
from app.models.costing import SteelPrice
from app.models.stamping import StampingPart
from app.models.stamping.tailor_weld_blank import StampingTailorWeldBlank
from app.models.yishiyiyi import StampingScrapPrice
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcAmounts
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostFailedItemVO
from app.services.costing.stamping_part_cost.calc.constants import (
    AMOUNT_QUANTIZE,
    FEE_QUANTIZE,
    UTIL_QUANTIZE,
    quantize,
)
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.stamping_part_cost.helpers import to_decimal


class TailorWeldPartCostCalculator:
    """拼焊总成核价：材料按子片相加，净重用父件焊后重量。"""

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
        blanks = list(part.tailor_weld_blanks or [])
        blanks = sorted(blanks, key=lambda b: (b.blank_seq or 0, b.id or 0))
        if len(blanks) < 2:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="拼焊件子片不足 2 片，无法按子片核算材料",
            )

        finished_total_kg = to_decimal(part.part_weight)
        if finished_total_kg is None:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="拼焊总成净重（焊后）为空",
            )

        kg_scale = Decimal("1000")
        scrap_kg_price = scrap_ton_price / kg_scale

        blank_kg_total = Decimal("0")
        material_amount_raw = Decimal("0")
        loss_scrap_raw = Decimal("0")
        steel_ids: list[int] = []
        steel_mills: list[str] = []
        steel_ton_prices: list[Decimal] = []
        blank_kgs: list[Decimal] = []

        for blank in blanks:
            blank_or_error = self._calc_blank_material(
                db,
                part=part,
                blank=blank,
                year=year,
                month=month,
                density=density,
                loss_rate=loss_rate,
                recovery_rate=recovery_rate,
                scrap_kg_price=scrap_kg_price,
            )
            if isinstance(blank_or_error, StampingPartCostFailedItemVO):
                return blank_or_error

            blank_kg, amount_sheet, loss_deduction, steel = blank_or_error
            blank_kg_total += blank_kg
            material_amount_raw += amount_sheet
            loss_scrap_raw += loss_deduction
            blank_kgs.append(blank_kg)
            steel_ids.append(steel.id)
            mill = (steel.steel_mill or "").strip()
            if mill:
                steel_mills.append(mill)
            steel_ton_prices.append(Decimal(str(steel.final_price_per_ton)))

        if blank_kg_total <= 0:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="预估单件材料消耗（各子片合计）计算结果无效",
            )

        scrap_kg = blank_kg_total - finished_total_kg
        utilization = quantize(
            (finished_total_kg / blank_kg_total) * Decimal("100"), UTIL_QUANTIZE
        )

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

        material_amount_sheet = quantize(material_amount_raw, AMOUNT_QUANTIZE)
        loss_scrap_deduction = quantize(loss_scrap_raw, AMOUNT_QUANTIZE)
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

        steel_price_id, steel_mill, steel_ton_price = self._steel_snapshot(
            steel_ids, steel_mills, steel_ton_prices, blank_kgs
        )

        return StampingPartCostCalcAmounts(
            density=density,
            material_loss_rate=loss_rate,
            scrap_recovery_rate=recovery_rate,
            blank_weight_kg=blank_kg_total,
            finished_total_kg=finished_total_kg,
            scrap_weight_kg=scrap_kg,
            material_utilization_pct=utilization,
            steel_price_id=steel_price_id,
            steel_mill=steel_mill,
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

    def _calc_blank_material(
        self,
        db: Session,
        *,
        part: StampingPart,
        blank: StampingTailorWeldBlank,
        year: int,
        month: int,
        density: Decimal,
        loss_rate: Decimal,
        recovery_rate: Decimal,
        scrap_kg_price: Decimal,
    ) -> (
        tuple[Decimal, Decimal, Decimal, SteelPrice]
        | StampingPartCostFailedItemVO
    ):
        blank_label = (
            blank.blank_part_number
            or f"{part.part_number}-{blank.blank_seq}"
        )
        material = (blank.material or "").strip()
        if not material:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason=f"子片 {blank_label} 材质为空，无法匹配钢材联动价",
            )

        sheet_length = to_decimal(blank.sheet_length)
        sheet_width = to_decimal(blank.sheet_width)
        thickness = to_decimal(blank.thickness)
        parts_per_sheet = blank.parts_per_sheet
        if parts_per_sheet is None:
            parts_per_sheet = part.parts_per_sheet

        if (
            sheet_length is None
            or sheet_width is None
            or thickness is None
            or parts_per_sheet is None
        ):
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason=f"子片 {blank_label} 料片尺寸/料厚/可制件数不完整",
            )
        if parts_per_sheet <= 0:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason=f"子片 {blank_label} 可制件数必须大于 0",
            )

        blank_kg = (
            sheet_length * sheet_width * thickness * density
        ) / Decimal("1000000") / Decimal(parts_per_sheet)
        if blank_kg <= 0:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason=f"子片 {blank_label} 材料消耗计算结果无效",
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
                reason=(
                    f"子片 {blank_label} 未匹配到钢材联动价"
                    f"（材质={material}, 料厚={thickness}）"
                ),
            )
        if len(steel_rows) > 1:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason=(
                    f"子片 {blank_label} 钢材联动价匹配到 {len(steel_rows)} 条，"
                    "中标场景应唯一，请检查数据"
                ),
            )
        steel = steel_rows[0]
        steel_kg_price = Decimal(str(steel.final_price_per_ton)) / Decimal("1000")

        # ①②按子片；③在总成 O 上一次算
        amount_sheet = blank_kg * steel_kg_price * (Decimal("1") + loss_rate)
        loss_deduction = blank_kg * loss_rate * recovery_rate * scrap_kg_price
        return blank_kg, amount_sheet, loss_deduction, steel

    @staticmethod
    def _steel_snapshot(
        steel_ids: list[int],
        steel_mills: list[str],
        steel_ton_prices: list[Decimal],
        blank_kgs: list[Decimal],
    ) -> tuple[int | None, str | None, Decimal | None]:
        """落库单列吨价：同价直接用；不同价按子片消耗量加权。"""
        unique_ids = list(dict.fromkeys(steel_ids))
        unique_prices = list(dict.fromkeys(steel_ton_prices))
        unique_mills = list(dict.fromkeys(steel_mills))
        mill = "/".join(unique_mills) if unique_mills else None
        if not steel_ton_prices:
            return None, mill, None

        steel_id = unique_ids[0] if len(unique_ids) == 1 else None
        if len(unique_prices) == 1:
            return steel_id, mill, unique_prices[0]

        total_kg = sum(blank_kgs, Decimal("0"))
        if total_kg <= 0 or len(blank_kgs) != len(steel_ton_prices):
            return None, mill, None
        weighted = (
            sum(
                (kg * price for kg, price in zip(blank_kgs, steel_ton_prices)),
                Decimal("0"),
            )
            / total_kg
        )
        return None, mill, quantize(weighted, Q4)
