"""
工程变更管线（指挥家第二步）。

职责边界：在同一业务 Session 内按序 flush——按变更单行种树/失效 → 采购对象 → 拆解 →
工艺按号增行一次 → 布点按号增行（软门禁可跳过），组装 effect_links（change_order_id 暂为变更单行下标）。
禁止：变更单落库与上传头标成功（persist）；禁止本文件内 commit。
依赖：树算法在 BomService；工艺/布点写入在 stamping 上游 Service。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import (
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    EFFECT_ASSEMBLY_L0,
)
from app.common.period import previous_month
from app.exceptions.base import BusinessException
from app.parsers.engineering_change.sheet_extract import SHEET_DIE, SHEET_PROCESS
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
from app.services.engineering_change.upload.persist.breakdown import persist_breakdown
from app.services.engineering_change.upload.persist.die import persist_die_parts
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
    warnings = list(prepared.warnings)
    links: list[EngineeringChangeEffectLinkInsert] = []
    sort_no = 0
    not_install_count = 0
    procurement_count = 0
    breakdown_count = 0
    has_bom_assembly = False
    prev_year, prev_month = previous_month(prepared.effective_year, prepared.effective_month)
    exclude_l0_ids = {item.before_root_id for item in prepared.change_orders}

    report_progress(on_progress, 40, "种树/失效")
    for change_order_index, item in enumerate(prepared.change_orders):
        tree_links, planted, not_install, plant_warnings = _plant_or_expire(
            db,
            prepared=prepared,
            item=item,
            change_order_index=change_order_index,
            sort_no=sort_no,
            prev_year=prev_year,
            prev_month=prev_month,
            current_user=current_user,
        )
        links.extend(tree_links)
        sort_no += len(tree_links)
        not_install_count += not_install
        has_bom_assembly = has_bom_assembly or planted
        warnings.extend(plant_warnings)
        new_l0_id = tree_links[0].after_id if tree_links else None

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
    process_links, process_count = persist_process_parts(
        db,
        process_sheet=prepared.sheets.get(SHEET_PROCESS),
        expire_new_part_numbers=prepared.revise_new_part_numbers,
        part_change_order_index=prepared.part_change_order_index,
        exclude_l0_ids=exclude_l0_ids,
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
    die_links, die_count, die_warnings = persist_die_parts(
        db,
        die_sheet=prepared.sheets.get(SHEET_DIE),
        expire_new_part_numbers=prepared.revise_new_part_numbers,
        part_change_order_index=prepared.part_change_order_index,
        exclude_l0_ids=exclude_l0_ids,
        has_revise=any(
            item.change_order.change_type == CHANGE_TYPE_REVISE for item in prepared.change_orders
        ),
        effective_year=prepared.effective_year,
        effective_month=prepared.effective_month,
        location=prepared.location,
        vehicle_model=prepared.vehicle_model,
        current_user=current_user,
        sort_no_start=sort_no,
        expiry_year=prepared.project_expiry_year,
        expiry_month=prepared.project_expiry_month,
    )
    links.extend(die_links)
    warnings.extend(die_warnings)

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
) -> tuple[list[EngineeringChangeEffectLinkInsert], bool, int, list[str]]:
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
            [],
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
        plant.warnings,
    )
