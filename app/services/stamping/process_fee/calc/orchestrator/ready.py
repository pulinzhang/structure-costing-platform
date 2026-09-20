"""加工费计算就绪统计。"""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.repositories.stamping.part.repository import StampingPartRepository
from app.repositories.stamping.process_fee.repository import (
    StampingProcessFeeRepository,
)
from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeCalcReadyVO
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService
from app.services.stamping.process_fee.calc.orchestrator.deps import ProcessFeeCalcDeps


class ProcessFeeCoverage(NamedTuple):
    complete: bool
    message: str
    part_count: int
    fee_count: int


def evaluate_process_fee_coverage(
    db: Session,
    *,
    year: int,
    aliases: list[str],
    vehicle_model: str,
    version: str | None = None,
    as_of_year: int | None = None,
    as_of_month: int | None = None,
    part_repo: StampingPartRepository | None = None,
    fee_repo: StampingProcessFeeRepository | None = None,
) -> ProcessFeeCoverage:
    """工艺零件是否都有对应加工费行（引擎补算与零件核价同一把钥匙）。"""
    part_repo = part_repo or StampingPartRepository()
    fee_repo = fee_repo or StampingProcessFeeRepository()
    parts = []
    fee_keys: set[tuple[str, str, str, str]] = set()
    use_as_of = as_of_year is not None and as_of_month is not None
    for alias in aliases:
        scoped_parts = part_repo.list_by_location_and_vehicle(
            db,
            location=alias,
            vehicle_model=vehicle_model,
            overlap_year=None if use_as_of else year,
            as_of_year=as_of_year if use_as_of else None,
            as_of_month=as_of_month if use_as_of else None,
        )
        if version is not None:
            scoped_parts = [part for part in scoped_parts if part.version == version]
        parts.extend(scoped_parts)
        for fee in fee_repo.list_by_scope(
            db,
            year=year,
            location=alias,
            vehicle_model=vehicle_model,
            version=version,
        ):
            if fee.final_processing_fee is None:
                continue
            fee_keys.add(
                (
                    fee.location,
                    fee.stamping_supplier or "",
                    fee.version or "",
                    fee.part_number,
                )
            )

    if not parts:
        return ProcessFeeCoverage(False, "无冲压零件", 0, 0)

    aligned = 0
    for part in parts:
        key = (
            part.location,
            part.stamping_supplier or "",
            part.version or "",
            part.part_number,
        )
        if key in fee_keys:
            aligned += 1

    part_count = len(parts)
    if aligned != part_count:
        return ProcessFeeCoverage(
            False,
            (
                f"冲压零件没有对应的加工费行"
                f"（工艺零件 {part_count} 条，对齐 {aligned} 条），"
                "请先完成冲压加工费计算"
            ),
            part_count,
            aligned,
        )
    return ProcessFeeCoverage(True, "冲压加工费已完成", part_count, aligned)


def collect_calc_ready(
    db: Session,
    deps: ProcessFeeCalcDeps,
    *,
    year: int,
    location: str | None = None,
    vehicle_model: str | None = None,
    version: str | None = None,
) -> StampingProcessFeeCalcReadyVO:
    if location and vehicle_model:
        try:
            VehicleModelService().require_overlaps_year(db, location, vehicle_model, year)
        except BusinessException as exc:
            return StampingProcessFeeCalcReadyVO(
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                version=version,
                part_count=0,
                tonnage_rate_count=0,
                message=str(exc),
            )
    if location:
        rates = deps.tonnage_repo.list_by_location_year(db, location, year)
    else:
        rates = deps.tonnage_repo.list_by_year(db, year)
    parts = []
    if location:
        parts = deps.part_repo.list_with_processes(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            overlap_year=year,
        )
    return StampingProcessFeeCalcReadyVO(
        year=year,
        location=location,
        stamping_supplier=None,
        vehicle_model=vehicle_model,
        version=version,
        part_count=len(parts),
        tonnage_rate_count=len(rates),
    )
