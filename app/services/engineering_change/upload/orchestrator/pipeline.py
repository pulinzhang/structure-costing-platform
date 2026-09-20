"""
工程变更管线（指挥家第二步）。

职责边界：在同一业务 Session 内按序 flush——按变更单行种树/失效 → 采购对象 → 拆解（从旧树结果抄）→
工艺按号增行一次 → 布点按变更单从旧号逻辑建立 → 检具费/模具费/包装/年度价有则抄到新号，组装 effect_links（change_order_id 暂为变更单行下标）。
禁止：变更单落库与上传头标成功（persist）；禁止本文件内 commit。
依赖：树算法在 BomService；工艺/布点/检具/模具费写入在 stamping 上游 Service；包装/年度价写入在 bom 上游 Service。
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import (
    CHANGE_TYPE_STOP,
    EFFECT_ASSEMBLY_L0,
)
from app.common.period import previous_month
from app.exceptions.base import BusinessException
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.upload.orchestrator.types import (
    PipelineBundle,
    PreparedBundle,
    PreparedChangeOrder,
    ProgressCallback,
    report_progress,
)
from app.services.engineering_change.upload.persist.annual_part_price import (
    persist_annual_part_prices,
)
from app.services.engineering_change.upload.persist.breakdown import persist_breakdown
from app.services.engineering_change.upload.persist.die import persist_die_parts
from app.services.engineering_change.upload.persist.die_fee import persist_die_fees
from app.services.engineering_change.upload.persist.gauge_fee import persist_gauge_fees
from app.services.engineering_change.upload.persist.packaging_fee import persist_packaging_fees
from app.services.engineering_change.upload.persist.process import persist_process_parts
from app.services.engineering_change.upload.persist.procurement import persist_procurement
from app.services.engineering_change.upload.persist.tree import (
    expire_l0_tree,
    plant_change_tree,
)


def run_engineering_change_pipeline(
    db: Session,
    prepared: PreparedBundle,
    *,
    current_user: UserVO,
    on_progress: ProgressCallback | None = None,
) -> PipelineBundle:
    warnings: list[str] = []
    links: list[EngineeringChangeEffectLinkInsert] = []
    sort_no = 0
    not_install_count = 0
    procurement_count = 0
    breakdown_count = 0
    has_bom_assembly = False
    prev_year, prev_month = previous_month(prepared.effective_year, prepared.effective_month)

    report_progress(on_progress, 40, "种树/失效")
    planted_after_ids: dict[str, int] = {}
    l0_old_to_new: dict[str, str] = {}
    l0_change_order_index: dict[str, int] = {}
    annual_source_id_remaps: list[tuple[dict[int, int], int]] = []
    for change_order_index, item in enumerate(prepared.change_orders):
        after_number = (item.change_order.after_assembly_part_number or "").strip()
        if after_number and after_number in planted_after_ids:
            links.append(
                EngineeringChangeEffectLinkInsert(
                    change_order_id=change_order_index,
                    effect_kind=EFFECT_ASSEMBLY_L0,
                    before_id=item.before_root_id,
                    after_id=planted_after_ids[after_number],
                    sort_no=sort_no,
                )
            )
            sort_no += 1
            has_bom_assembly = True
            continue
        tree_links, planted, not_install, source_id_remap = _plant_or_expire(
            db,
            prepared=prepared,
            item=item,
            change_order_index=change_order_index,
            sort_no=sort_no,
            prev_year=prev_year,
            prev_month=prev_month,
            current_user=current_user,
            extra_change_orders=_sibling_change_orders(prepared.change_orders, change_order_index),
        )
        links.extend(tree_links)
        sort_no += len(tree_links)
        not_install_count += not_install
        has_bom_assembly = has_bom_assembly or planted
        new_l0_id = tree_links[0].after_id if tree_links else None
        if after_number and new_l0_id is not None:
            planted_after_ids[after_number] = new_l0_id
            before_l0 = item.change_order.before_assembly_part_number.strip()
            if before_l0 and before_l0 != after_number:
                l0_old_to_new[before_l0] = after_number
                l0_change_order_index[after_number] = change_order_index
            if source_id_remap:
                annual_source_id_remaps.append((source_id_remap, change_order_index))

        report_progress(on_progress, 70, "采购对象与拆解")
        procurement = persist_procurement(
            db,
            change_order=item.change_order,
            after_root_id=new_l0_id,
            current_user=current_user,
            sort_no_start=sort_no,
            change_order_id=change_order_index,
        )
        links.extend(procurement.effect_links)
        sort_no += len(procurement.effect_links)
        procurement_count += procurement.inserted_count
        breakdown = persist_breakdown(
            db,
            change_order=item.change_order,
            after_root_id=new_l0_id,
            source_id_remap=source_id_remap,
            current_user=current_user,
            sort_no_start=sort_no,
            change_order_id=change_order_index,
        )
        links.extend(breakdown.effect_links)
        sort_no += len(breakdown.effect_links)
        breakdown_count += breakdown.inserted_count
        warnings.extend(procurement.warnings)
        warnings.extend(breakdown.warnings)

    report_progress(on_progress, 90, "工艺与布点")
    process_links, process_count, process_version = persist_process_parts(
        db,
        file_content=prepared.file_content,
        revise_old_to_new=prepared.revise_old_to_new,
        part_change_order_index=prepared.part_change_order_index,
        effective_year=prepared.effective_year,
        effective_month=prepared.effective_month,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        current_user=current_user,
        sort_no_start=sort_no,
        expiry_year=prepared.project_expiry_year,
        expiry_month=prepared.project_expiry_month,
    )
    links.extend(process_links)
    sort_no += len(process_links)
    die_links, die_count, new_die_part_ids = persist_die_parts(
        db,
        revise_old_to_new=prepared.revise_old_to_new,
        part_change_order_index=prepared.part_change_order_index,
        effective_year=prepared.effective_year,
        effective_month=prepared.effective_month,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        current_user=current_user,
        sort_no_start=sort_no,
        version=process_version or None,
        expiry_year=prepared.project_expiry_year,
        expiry_month=prepared.project_expiry_month,
    )
    links.extend(die_links)
    sort_no += len(die_links)

    report_progress(on_progress, 94, "检具费与模具费")
    gauge_links = persist_gauge_fees(
        db,
        revise_old_to_new=prepared.revise_old_to_new,
        part_change_order_index=prepared.part_change_order_index,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        current_user=current_user,
        sort_no_start=sort_no,
    )
    links.extend(gauge_links)
    sort_no += len(gauge_links)
    die_fee_links = persist_die_fees(
        db,
        revise_old_to_new=prepared.revise_old_to_new,
        part_change_order_index=prepared.part_change_order_index,
        new_die_part_ids=new_die_part_ids,
        effective_year=prepared.effective_year,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        current_user=current_user,
        sort_no_start=sort_no,
    )
    links.extend(die_fee_links)
    sort_no += len(die_fee_links)

    report_progress(on_progress, 96, "包装与年度价")
    packaging_links = persist_packaging_fees(
        db,
        revise_old_to_new=l0_old_to_new,
        part_change_order_index=l0_change_order_index,
        effective_year=prepared.effective_year,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        current_user=current_user,
        sort_no_start=sort_no,
    )
    links.extend(packaging_links)
    sort_no += len(packaging_links)
    annual_links = persist_annual_part_prices(
        db,
        source_id_remaps=annual_source_id_remaps,
        effective_year=prepared.effective_year,
        location=prepared.location,
        current_user=current_user,
        sort_no_start=sort_no,
    )
    links.extend(annual_links)

    return PipelineBundle(
        not_install_count=not_install_count,
        process_inserted_count=process_count,
        die_inserted_count=die_count,
        procurement_inserted_count=procurement_count,
        breakdown_inserted_count=breakdown_count,
        has_bom_assembly=has_bom_assembly,
        effect_links=links,
        warnings=warnings,
    )


def _plant_or_expire(
    db: Session,
    *,
    prepared: PreparedBundle,
    item: PreparedChangeOrder,
    change_order_index: int,
    sort_no: int,
    prev_year: int,
    prev_month: int,
    current_user: UserVO,
    extra_change_orders: Sequence[ChangeOrderRowParsed] = (),
) -> tuple[list[EngineeringChangeEffectLinkInsert], bool, int, dict[int, int]]:
    change_order = item.change_order
    if change_order.change_type == CHANGE_TYPE_STOP:
        expire_l0_tree(
            db,
            l0_id=item.before_root_id,
            expiry_year=prev_year,
            expiry_month=prev_month,
            current_user=current_user,
        )
        return (
            [
                EngineeringChangeEffectLinkInsert(
                    change_order_id=change_order_index,
                    effect_kind=EFFECT_ASSEMBLY_L0,
                    before_id=item.before_root_id,
                    after_id=None,
                    sort_no=sort_no,
                )
            ],
            True,
            0,
            {},
        )
    if item.sliced_bom_nodes is None:
        raise BusinessException("缺车身件材料清单")
    plant = plant_change_tree(
        db,
        snapshot_id=item.snapshot_id,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        before_l0_id=item.before_root_id,
        seq_no=item.before_seq_no,
        change_order=change_order,
        parsed_nodes=item.sliced_bom_nodes,
        extra_change_orders=extra_change_orders,
        effective_year=prepared.effective_year,
        effective_month=prepared.effective_month,
        expiry_year=prepared.project_expiry_year,
        expiry_month=prepared.project_expiry_month,
        current_user=current_user,
        node_bom_version=prepared.node_bom_version,
    )
    expire_l0_tree(
        db,
        l0_id=item.before_root_id,
        expiry_year=prev_year,
        expiry_month=prev_month,
        current_user=current_user,
    )
    return (
        [
            EngineeringChangeEffectLinkInsert(
                change_order_id=change_order_index,
                effect_kind=EFFECT_ASSEMBLY_L0,
                before_id=item.before_root_id,
                after_id=plant.new_l0_id,
                sort_no=sort_no,
            )
        ],
        True,
        plant.not_install_count,
        plant.source_id_remap,
    )


def _sibling_change_orders(
    items: list[PreparedChangeOrder],
    index: int,
) -> list[ChangeOrderRowParsed]:
    current = items[index].change_order
    after = (current.after_assembly_part_number or "").strip()
    before = current.before_assembly_part_number.strip()
    if not after:
        return []
    siblings: list[ChangeOrderRowParsed] = []
    for later in items[index + 1 :]:
        other = later.change_order
        if other.change_type == CHANGE_TYPE_STOP:
            continue
        if (
            other.before_assembly_part_number.strip() == before
            and (other.after_assembly_part_number or "").strip() == after
        ):
            siblings.append(other)
    return siblings
