"""当月材料：向冲压要工艺列，再叠本通道成功切点。冲压不回调这里。"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.engineering_change.material_change.order import EngineeringChangeMaterialOrder
from app.repositories.engineering_change.material_change.order_repository import (
    MaterialChangeOrderRepository,
)
from app.repositories.stamping.part.types import MaterialAsOfIdentity
from app.services.stamping.part.engineering.service import StampingEngineeringService

_order_repo = MaterialChangeOrderRepository()


def apply_after_material(
    process_material: str | None,
    orders: Sequence[EngineeringChangeMaterialOrder],
    *,
    as_of_year: int,
    as_of_month: int,
    exclude_upload_log_id: int | None = None,
) -> str | None:
    """生效月 ≤ as_of 的最后一刀 after_material。无切点 = 工艺列。"""
    latest = process_material
    as_of = (as_of_year, as_of_month)
    for order in orders:
        if exclude_upload_log_id is not None and order.upload_log_id == exclude_upload_log_id:
            continue
        if (order.effective_year, order.effective_month) <= as_of:
            latest = order.after_material
    return latest


def resolve_material(
    db: Session,
    *,
    location: str,
    stamping_supplier: str,
    vehicle_model: str,
    part_number: str,
    as_of_year: int,
    as_of_month: int,
    exclude_upload_log_id: int | None = None,
) -> str | None:
    """不含 exclude 的本本。无切点 = 工艺列。"""
    part, miss = StampingEngineeringService().get_part_as_of(
        db,
        location=location,
        stamping_supplier=stamping_supplier,
        vehicle_model=vehicle_model,
        part_number=part_number,
        as_of_year=as_of_year,
        as_of_month=as_of_month,
    )
    if miss or part is None:
        return None
    orders = _order_repo.list_success_for_identity(
        db,
        location=location,
        stamping_supplier=stamping_supplier,
        vehicle_model=vehicle_model,
        part_number=part_number,
    )
    return apply_after_material(
        part.material,
        orders,
        as_of_year=as_of_year,
        as_of_month=as_of_month,
        exclude_upload_log_id=exclude_upload_log_id,
    )


def overlay_materials_for_parts(
    db: Session,
    identities: Sequence[MaterialAsOfIdentity],
    year: int,
    month: int,
) -> dict[int, str]:
    """按身份批量叠成功切点。键含冲压工厂，同号不同厂不混。"""
    if not identities:
        return {}
    location = identities[0]["location"]
    grouped: dict[tuple[str, str, str, str], list[EngineeringChangeMaterialOrder]] = defaultdict(
        list
    )
    for order in _order_repo.list_success_in_location(db, location=location):
        grouped[
            (order.location, order.stamping_supplier, order.vehicle_model, order.part_number)
        ].append(order)
    resolved: dict[int, str] = {}
    for identity in identities:
        key = (
            identity["location"],
            identity["stamping_supplier"],
            identity["vehicle_model"],
            identity["part_number"],
        )
        material = apply_after_material(
            identity["material"],
            grouped.get(key, []),
            as_of_year=year,
            as_of_month=month,
        )
        resolved[identity["part_id"]] = material or ""
    return resolved
