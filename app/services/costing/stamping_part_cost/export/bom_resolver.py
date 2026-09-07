"""总成供货号（BOM L0）解析。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.services.costing.stamping_part_cost.export.bom_map import build_part_to_l0_map
from app.services.masterdata.location.location_service import LocationService


def resolve_assembly_supply_no(
    db: Session,
    *,
    bom_snapshot_repo: BomSnapshotRepository,
    bom_node_repo: BomNodeRepository,
    location: str | None,
    vehicle_model: str | None,
    version: str | None,
    part_number: str | None,
    snapshot_l0_cache: dict[tuple[str, str, str], dict[str, str]],
) -> str:
    """
    沿 BOM parent_id 上溯至 L0，取其零件号作为总成供货号。
    同一零件挂多个 L0 时逗号分隔。BOM 查询须基地相同（兼容「青岛/青岛基地」写法）。

    匹配顺序：
    1) 同基地 + vehicle_model + version(=bom_version) 精确命中
    2) 同基地 + vehicle_model 下回退（工艺版本与 BOM 版本号可能不一致）
    """
    loc = (location or "").strip()
    model = (vehicle_model or "").strip()
    bom_version = (version or "").strip()
    pn = (part_number or "").strip()
    if not loc or not model or not pn:
        return ""

    part_to_l0: dict[str, str] | None = None

    # 1) 精确版本
    if bom_version:
        names = LocationService().expand_for_query(db, loc)
        for candidate_location in names:
            key = (candidate_location, model, bom_version)
            if key in snapshot_l0_cache:
                part_to_l0 = snapshot_l0_cache[key]
                break
            snapshot = bom_snapshot_repo.get_by_unique_key(
                db,
                location=candidate_location,
                vehicle_model=model,
                bom_version=bom_version,
            )
            if snapshot is None:
                continue
            part_to_l0 = build_part_to_l0_map(bom_node_repo.list_by_snapshot(db, snapshot.id))
            snapshot_l0_cache[key] = part_to_l0
            break

    # 2) 同车型最新 BOM 回退
    if part_to_l0 is None or (part_to_l0 is not None and pn not in part_to_l0):
        names = LocationService().expand_for_query(db, loc)
        for candidate_location in names:
            fallback_key = (candidate_location, model, "__latest__")
            if fallback_key in snapshot_l0_cache:
                fallback_map = snapshot_l0_cache[fallback_key]
            else:
                snapshots = bom_snapshot_repo.list_by_location_model(
                    db,
                    location=candidate_location,
                    vehicle_model=model,
                )
                if not snapshots:
                    snapshot_l0_cache[fallback_key] = {}
                    continue
                # 优先选包含该零件号的 snapshot；否则取最新
                chosen = None
                for snap in snapshots:
                    nodes = bom_node_repo.list_by_snapshot(db, snap.id)
                    mapping = build_part_to_l0_map(nodes)
                    snap_key = (
                        candidate_location,
                        model,
                        (snap.bom_version or "").strip() or f"id:{snap.id}",
                    )
                    snapshot_l0_cache[snap_key] = mapping
                    if pn in mapping:
                        chosen = mapping
                        break
                    if chosen is None:
                        chosen = mapping
                snapshot_l0_cache[fallback_key] = chosen or {}
                fallback_map = snapshot_l0_cache[fallback_key]

            if fallback_map:
                part_to_l0 = fallback_map
                if pn in fallback_map:
                    break

    if not part_to_l0:
        empty_key = (loc, model, bom_version or "__latest__")
        snapshot_l0_cache.setdefault(empty_key, {})
        return ""

    return part_to_l0.get(pn, "")
