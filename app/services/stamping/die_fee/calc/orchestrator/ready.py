"""模具费计算就绪统计。"""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.repositories.stamping.die.repository import StampingDiePartRepository
from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.schemas.vo.stamping_die_fee_vo import StampingDieFeeCalcReadyVO
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService
from app.services.stamping.die_fee.calc.orchestrator.deps import DieFeeCalcDeps
from app.services.stamping.die_fee.calc.orchestrator.identity import (
    matches_part,
    parts_for_identity,
    strip_optional,
)
from app.services.stamping.die_fee.calc.weight_resolver import PreviousWeightIndex
from app.services.stamping.die_fee.rules.fee_math import ZERO


class DieFeeCoverage(NamedTuple):
    """引擎年度补算：有布点且当年有任意模具费行 → complete。"""

    complete: bool
    has_dies: bool
    message: str
    part_count: int
    fee_count: int


def evaluate_die_fee_coverage(
    db: Session,
    *,
    year: int,
    aliases: list[str],
    vehicle_model: str,
    die_repo: StampingDiePartRepository | None = None,
    fee_repo: StampingDieFeeRepository | None = None,
) -> DieFeeCoverage:
    """布点年交集有件且 fee 行 > 0 视为已齐；无布点 has_dies=False（引擎不列入计划）。"""
    die_repo = die_repo or StampingDiePartRepository()
    fee_repo = fee_repo or StampingDieFeeRepository()
    part_count = 0
    fee_count = 0
    for alias in aliases:
        parts = die_repo.list_with_processes(
            db,
            location=alias,
            vehicle_model=vehicle_model,
            overlap_year=year,
        )
        part_count += len(parts)
        fee_count += fee_repo.count_by_year_location(
            db,
            year=year,
            location=alias,
            vehicle_model=vehicle_model,
        )

    if part_count <= 0:
        return DieFeeCoverage(False, False, "无模具布点", 0, fee_count)
    if fee_count <= 0:
        return DieFeeCoverage(
            False,
            True,
            f"有模具布点 {part_count} 件，当年无模具费结果，将自动补算",
            part_count,
            0,
        )
    return DieFeeCoverage(
        True,
        True,
        f"冲压模具费已有结果（布点 {part_count}，费用行 {fee_count}）",
        part_count,
        fee_count,
    )


def collect_calc_ready(
    db: Session,
    deps: DieFeeCalcDeps,
    *,
    year: int,
    location: str | None = None,
    vehicle_model: str | None = None,
    version: str | None = None,
) -> StampingDieFeeCalcReadyVO:
    version_filter = strip_optional(version)
    has_unit_price = False
    calculable_count = 0
    part_count = 0
    if location and vehicle_model:
        try:
            VehicleModelService().require_overlaps_year(db, location, vehicle_model, year)
        except BusinessException as exc:
            return StampingDieFeeCalcReadyVO(
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                version=version_filter,
                part_count=0,
                calculable_count=0,
                has_unit_price=False,
                message=str(exc),
            )
        all_parts = deps.die_repo.list_with_processes(
            db,
            location=location,
            vehicle_model=vehicle_model,
            overlap_year=year,
        )
        persist_parts = parts_for_identity(
            all_parts,
            stamping_supplier=None,
            version=version_filter,
        )
        part_count = len(persist_parts)
        price = deps.unit_price_repo.get_effective(
            db, location=location, vehicle_model=vehicle_model
        )
        has_unit_price = (
            price is not None and price.allocation_qty is not None and price.allocation_qty > ZERO
        )
        previous_weights = PreviousWeightIndex()
        if has_unit_price and price is not None:
            for part in all_parts:
                calculated, previous_weights = deps.part_calculator.calc_part(
                    part,
                    steel_plate_unit_price=price.steel_plate_unit_price,
                    progressive_die_unit_price=price.progressive_die_unit_price,
                    allocation_qty=price.allocation_qty,
                    previous_weights=previous_weights,
                )
                if calculated is not None and matches_part(
                    part,
                    stamping_supplier=None,
                    version=version_filter,
                ):
                    calculable_count += 1
    return StampingDieFeeCalcReadyVO(
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        stamping_supplier=None,
        version=version_filter,
        part_count=part_count,
        calculable_count=calculable_count,
        has_unit_price=has_unit_price,
    )
