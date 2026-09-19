"""项目：代号规范化、生效窗口、引入门禁。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.period import is_in_period as columns_in_period
from app.common.period import overlaps_year as period_overlaps_year
from app.common.period import period, validate_period
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.vehicle_model import VehicleModel
from app.repositories.masterdata.vehicle_model import VehicleModelRepository
from app.schemas.vo.vehicle_model_vo import (
    PERIOD_EXPIRED,
    PERIOD_INTRODUCIBLE,
    PERIOD_PENDING,
    VehicleModelVO,
)
from app.services.masterdata.location import LocationService

PLACEHOLDER_CODES = frozenset({"UNKNOWN"})
PAGE_HINT = "请到项目一览手工增加或上传（#/vehicle-model-list）"
FILE_MISMATCH = "文件项目为 {parsed}，与填写的项目 {selected} 不一致"

__all__ = [
    "FILE_MISMATCH",
    "PAGE_HINT",
    "PLACEHOLDER_CODES",
    "assert_matches_selected",
    "is_in_period",
    "is_not_expired",
    "list_filter_codes",
    "list_introducible",
    "list_overlaps_year",
    "list_registered",
    "normalize",
    "overlaps_year",
    "period",
    "period_status",
    "require_introducible",
    "require_introducible_by_code",
    "require_overlaps_year",
    "require_registered",
    "require_row",
    "to_vo",
    "validate_period",
]


def normalize(value: str | None) -> str | None:
    code = normalize_vehicle_model(value)
    if not code or code in PLACEHOLDER_CODES:
        return None
    return code


def to_vo(record: VehicleModel, period_status: str) -> VehicleModelVO:
    return VehicleModelVO(
        location=record.location,
        vehicle_model=record.vehicle_model,
        effective_year=record.effective_year,
        effective_month=record.effective_month,
        expiry_year=record.expiry_year,
        expiry_month=record.expiry_month,
        current_supplied_units=record.current_supplied_units,
        period_status=period_status,
    )


def require_row(
    repository: VehicleModelRepository,
    location: str,
    vehicle_model: str,
    db: Session,
) -> VehicleModel:
    name = (location or "").strip()
    code = normalize(vehicle_model)
    if not name or not code:
        raise NotFoundException("项目不存在")
    record = repository.get(db, name, code)
    if record is None:
        raise NotFoundException("项目不存在")
    return record


def is_not_expired(record: VehicleModel, year: int, month: int) -> bool:
    if record.expiry_year is None or record.expiry_month is None:
        return True
    return period(year, month) <= period(record.expiry_year, record.expiry_month)


def is_in_period(record: VehicleModel, year: int, month: int) -> bool:
    return columns_in_period(
        effective_year=record.effective_year,
        effective_month=record.effective_month,
        expiry_year=record.expiry_year,
        expiry_month=record.expiry_month,
        as_of_year=year,
        as_of_month=month,
    )


def overlaps_year(record: VehicleModel, year: int) -> bool:
    return period_overlaps_year(
        effective_year=record.effective_year,
        effective_month=record.effective_month,
        expiry_year=record.expiry_year,
        expiry_month=record.expiry_month,
        year=year,
    )


def period_status(record: VehicleModel, year: int, month: int) -> str:
    as_of = period(year, month)
    if as_of < period(record.effective_year, record.effective_month):
        return PERIOD_PENDING
    if not is_not_expired(record, year, month):
        return PERIOD_EXPIRED
    return PERIOD_INTRODUCIBLE


def require_registered(
    repository: VehicleModelRepository,
    db: Session,
    location: str,
    vehicle_model: str,
) -> str:
    code = normalize(vehicle_model)
    if not code:
        raise BusinessException(f"没有该项目，{PAGE_HINT}")
    record = repository.get(db, location, code)
    if record is None:
        raise BusinessException(f"没有该项目，{PAGE_HINT}")
    return record.vehicle_model


def require_introducible(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
    location: str,
    vehicle_model: str,
    year: int,
    month: int,
) -> tuple[str, str]:
    canonical = location_service.require_enabled(db, location)
    code = normalize(vehicle_model)
    if not code:
        raise BusinessException(f"没有该项目，{PAGE_HINT}")
    record = repository.get(db, canonical, code)
    if record is None:
        raise BusinessException(f"没有该项目，{PAGE_HINT}")
    as_of = period(year, month)
    if as_of < period(record.effective_year, record.effective_month):
        raise BusinessException(f"该项目尚未生效，{PAGE_HINT}")
    if not is_not_expired(record, year, month):
        raise BusinessException(f"该项目已失效，{PAGE_HINT}")
    return (canonical, record.vehicle_model)


def require_introducible_by_code(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
    vehicle_model: str,
    year: int,
    month: int,
) -> tuple[str, str]:
    """文件识别项目代号：唯一可引入行带出所属基地。"""
    code = normalize(vehicle_model)
    if not code:
        raise BusinessException(f"没有该项目，{PAGE_HINT}")
    rows = repository.list_by_code(db, code)
    if not rows:
        raise BusinessException(f"没有该项目，{PAGE_HINT}")

    introducible: list[VehicleModel] = []
    for record in rows:
        try:
            location_service.require_enabled(db, record.location)
        except BusinessException:
            continue
        if is_in_period(record, year, month):
            introducible.append(record)

    if len(introducible) == 1:
        chosen = introducible[0]
        return (chosen.location, chosen.vehicle_model)
    if len(introducible) > 1:
        names = "、".join(row.location for row in introducible)
        raise BusinessException(
            f"项目 {code} 挂在多个可引入基地（{names}），无法自动确定。" f"{PAGE_HINT}"
        )
    if len(rows) == 1:
        return require_introducible(
            repository, location_service, db, rows[0].location, code, year, month
        )
    raise BusinessException(f"没有可引入的项目 {code}，{PAGE_HINT}")


def require_overlaps_year(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
    location: str,
    vehicle_model: str,
    year: int,
) -> tuple[str, str]:
    canonical = location_service.require_enabled(db, location)
    code = normalize(vehicle_model)
    if not code:
        raise BusinessException(f"没有该项目，{PAGE_HINT}")
    record = repository.get(db, canonical, code)
    if record is None:
        raise BusinessException(f"没有该项目，{PAGE_HINT}")
    if not overlaps_year(record, year):
        raise BusinessException(f"该项目与 {year} 年无交集，{PAGE_HINT}")
    return (canonical, record.vehicle_model)


def assert_matches_selected(selected: str | None, parsed: str | None) -> None:
    selected_code = normalize(selected)
    parsed_code = normalize(parsed)
    if not selected_code or not parsed_code or selected_code != parsed_code:
        raise BusinessException(
            FILE_MISMATCH.format(
                parsed=parsed_code or (parsed or "").strip() or "空",
                selected=selected_code or (selected or "").strip() or "空",
            )
        )


def list_introducible(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
    location: str,
    year: int,
    month: int,
) -> list[str]:
    canonical = location_service.resolve_canonical(db, location)
    if canonical is None:
        return []
    try:
        location_service.require_enabled(db, canonical)
    except BusinessException:
        return []
    return [
        row.vehicle_model
        for row in repository.list_by_location(db, canonical)
        if is_in_period(row, year, month)
    ]


def list_registered(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
    location: str,
) -> list[str]:
    canonical = location_service.resolve_canonical(db, location)
    if canonical is None:
        return []
    return [row.vehicle_model for row in repository.list_by_location(db, canonical)]


def list_filter_codes(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
    location: str | None = None,
) -> list[str]:
    """列表筛：有基地则该基地已登记；无则各基地代号并集。"""
    raw = (location or "").strip()
    if raw:
        return list_registered(repository, location_service, db, raw)
    return repository.list_distinct_codes(db)


def list_overlaps_year(
    repository: VehicleModelRepository,
    location_service: LocationService,
    db: Session,
    location: str,
    year: int,
) -> list[str]:
    canonical = location_service.resolve_canonical(db, location)
    if canonical is None:
        return []
    try:
        location_service.require_enabled(db, canonical)
    except BusinessException:
        return []
    return [
        row.vehicle_model
        for row in repository.list_by_location(db, canonical)
        if overlaps_year(row, year)
    ]
