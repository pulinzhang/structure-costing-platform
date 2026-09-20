"""计算开场：布点、单价、已审冲突。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED
from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.stamping.die import StampingDiePart
from app.models.stamping.die_unit_price import StampingDieUnitPrice
from app.schemas.dto.stamping_die_fee_dto import StampingDieFeeCalcDTO
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService
from app.services.stamping.die_fee.calc.constants import APPROVED_SCOPE_MESSAGE
from app.services.stamping.die_fee.calc.orchestrator.deps import DieFeeCalcDeps
from app.services.stamping.die_fee.calc.orchestrator.identity import parts_for_identity
from app.services.stamping.die_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.stamping.die_fee.rules.fee_math import ZERO


@dataclass(slots=True)
class CalcPrepContext:
    parts: list[StampingDiePart]
    persist_parts: list[StampingDiePart]
    price: StampingDieUnitPrice
    started_at: datetime
    detail_lines: list[str]
    scrap_byproduct_keys: frozenset[tuple[str, str, str]]


def count_approved(db: Session, deps: DieFeeCalcDeps, dto: StampingDieFeeCalcDTO) -> int:
    return deps.fee_repo.count_by_scope_and_statuses(
        db,
        year=dto.year,
        location=dto.location,
        vehicle_model=dto.vehicle_model,
        statuses=[AUDIT_APPROVED],
        version=dto.version,
    )


def prepare_calc_run(
    db: Session,
    deps: DieFeeCalcDeps,
    dto: StampingDieFeeCalcDTO,
    progress: ProgressNotifier,
) -> CalcPrepContext:
    location, vehicle_model = VehicleModelService().require_overlaps_year(
        db, dto.location, dto.vehicle_model, dto.year
    )
    started_at = now()
    version_filter = dto.version
    version_bit = f"version={version_filter}" if version_filter else ""
    detail_lines = [
        (
            f"开始计算 year={dto.year} location={location} "
            f"vehicle={vehicle_model} supplier=全部工厂"
            + (f" {version_bit}" if version_bit else "")
        )
    ]
    progress.report(8, "加载模具布点...")
    parts = deps.die_repo.list_with_processes(
        db,
        location=location,
        vehicle_model=vehicle_model,
        overlap_year=dto.year,
    )
    if not parts:
        raise BusinessException(
            f"基地「{location}」项目「{vehicle_model}」" f"在 {dto.year} 年没有有效期内的模具布点"
        )

    persist_parts = parts_for_identity(
        parts,
        stamping_supplier=None,
        version=version_filter,
    )
    if version_filter and not persist_parts:
        raise BusinessException("所选版本下无有效期内模具布点")

    progress.report(15, "加载模具单价...")
    price = deps.unit_price_repo.get_effective(db, location=location, vehicle_model=vehicle_model)
    if price is None or price.allocation_qty <= ZERO:
        raise BusinessException(
            f"基地「{location}」项目「{vehicle_model}」无生效模具单价或分摊万台无效"
        )

    if count_approved(
        db,
        deps,
        dto.model_copy(
            update={
                "location": location,
                "vehicle_model": vehicle_model,
            }
        ),
    ):
        raise BusinessException(APPROVED_SCOPE_MESSAGE, code=409)

    scrap_byproduct_keys = deps.part_repo.list_scrap_byproduct_keys(
        db, location=location, vehicle_model=vehicle_model
    )
    return CalcPrepContext(
        parts=parts,
        persist_parts=persist_parts,
        price=price,
        started_at=started_at,
        detail_lines=detail_lines,
        scrap_byproduct_keys=scrap_byproduct_keys,
    )
