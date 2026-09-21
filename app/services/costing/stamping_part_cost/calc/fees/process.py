"""加工费：取年度加工费确认单价；缺档或空单价否决本件，不记 0。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.stamping import StampingPart
from app.repositories.stamping.process_fee.repository import (
    StampingProcessFeeRepository,
)
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostFailedItemVO
from app.services.costing.stamping_part_cost.calc.constants import FEE_QUANTIZE, quantize


@dataclass(frozen=True, slots=True)
class ProcessFeeLookup:
    process_fee_id: int
    process_fee_amount: Decimal


class ProcessFeeResolver:
    """只负责加工费。与模具费、检具费分档、分公式。"""

    def __init__(self, process_fee_repo: StampingProcessFeeRepository | None = None) -> None:
        self.process_fee_repo = process_fee_repo or StampingProcessFeeRepository()

    def lookup(
        self,
        db: Session,
        *,
        part: StampingPart,
        year: int,
        supplier: str,
    ) -> ProcessFeeLookup | StampingPartCostFailedItemVO:
        fee = self.process_fee_repo.get_by_business_key(
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
                reason="加工费确认单价为空，请先完成加工费计算或录入其它费用",
            )
        return ProcessFeeLookup(
            process_fee_id=fee.id,
            process_fee_amount=quantize(Decimal(str(fee.final_processing_fee)), FEE_QUANTIZE),
        )
