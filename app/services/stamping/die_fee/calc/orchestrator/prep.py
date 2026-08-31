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
from app.services.stamping.die_fee.calc.constants import APPROVED_SCOPE_MESSAGE
from app.services.stamping.die_fee.calc.orchestrator.deps import DieFeeCalcDeps
from app.services.stamping.die_fee.calc.orchestrator.identity import parts_for_identity
from app.services.stamping.die_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.stamping.die_fee.fee_math import ZERO


@dataclass(slots=True)
class CalcPrepContext:
    parts: list[StampingDiePart]
    persist_parts: list[StampingDiePart]
    price: StampingDieUnitPrice
    started_at: datetime
    detail_lines: list[str]


def count_approved(db: Session, deps: DieFeeCalcDeps, dto: StampingDieFeeCalcDTO) -> int:
    return deps.fee_repo.count_by_scope_and_statuses(
        db,
        year=dto.year,
        location=dto.location,
        vehicle_model=dto.vehicle_model,
        statuses=[AUDIT_APPROVED],
        stamping_supplier=dto.stamping_supplier,
        version=dto.version,
    )


def prepare_calc_run(
    db: Session,
    deps: DieFeeCalcDeps,
    dto: StampingDieFeeCalcDTO,
    progress: ProgressNotifier,
) -> CalcPrepContext:
    started_at = now()
    supplier_filter = dto.stamping_supplier
    version_filter = dto.version
    identity_bits = [
        f"supplier={supplier_filter}" if supplier_filter else "",
        f"version={version_filter}" if version_filter else "",
    ]
    identity_label = " ".join(bit for bit in identity_bits if bit) or "全部供应商/版本"
    detail_lines = [
        (
            f"开始计算 year={dto.year} location={dto.location} "
            f"vehicle={dto.vehicle_model} {identity_label}"
        )
    ]
    progress.report(8, "加载模具布点...")
    parts = deps.die_repo.list_with_processes(
        db, location=dto.location, vehicle_model=dto.vehicle_model
    )
    if not parts:
        raise BusinessException(f"基地「{dto.location}」项目「{dto.vehicle_model}」无模具布点")

    persist_parts = parts_for_identity(
        parts,
        stamping_supplier=supplier_filter,
        version=version_filter,
    )
    if (supplier_filter or version_filter) and not persist_parts:
        raise BusinessException("所选供应商/版本下无模具布点")

    progress.report(15, "加载模具单价...")
    price = deps.unit_price_repo.get_effective(
        db, location=dto.location, vehicle_model=dto.vehicle_model
    )
    if price is None or price.allocation_qty <= ZERO:
        raise BusinessException(
            f"基地「{dto.location}」项目「{dto.vehicle_model}」无生效模具单价或分摊万台无效"
        )

    if count_approved(db, deps, dto):
        raise BusinessException(APPROVED_SCOPE_MESSAGE, code=409)

    return CalcPrepContext(
        parts=parts,
        persist_parts=persist_parts,
        price=price,
        started_at=started_at,
        detail_lines=detail_lines,
    )
