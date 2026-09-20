"""焊接工艺拆解：未审核节点下的工艺明细改写。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, audit_update
from app.common.bom.welding_standard_process import (
    all_standard_process_names,
    resolve_standard_process_name,
    resolve_standard_process_unit,
)
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownLineBatchItemDTO,
    BomWeldingProcessBreakdownLinePatch,
    BomWeldingProcessBreakdownLineUpdateDTO,
    BomWeldingProcessBreakdownNodeLinesUpdateDTO,
    BomWeldingProcessBreakdownNodePatch,
)
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    BomWeldingProcessBreakdownLineVO,
    BomWeldingProcessBreakdownNodeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_process_breakdown.query import (
    get_node,
    resolve_breakdown_tree_root_version,
)
from app.services.bom.welding_process_breakdown.recompute import (
    recompute_scope_derived_fields,
)

_STANDARD_PROCESS_NAMES = frozenset(all_standard_process_names())


def line_patch_from_dto(
    dto: BomWeldingProcessBreakdownLineUpdateDTO | BomWeldingProcessBreakdownLineBatchItemDTO,
) -> BomWeldingProcessBreakdownLinePatch:
    patch: BomWeldingProcessBreakdownLinePatch = {}
    if "process_token" in dto.model_fields_set:
        patch["process_token"] = dto.process_token
    if "process_qty" in dto.model_fields_set:
        patch["process_qty"] = dto.process_qty
    if "process_qty_unit" in dto.model_fields_set:
        patch["process_qty_unit"] = dto.process_qty_unit
    if "process_qty_secondary" in dto.model_fields_set:
        patch["process_qty_secondary"] = dto.process_qty_secondary
    if "process_qty_secondary_unit" in dto.model_fields_set:
        patch["process_qty_secondary_unit"] = dto.process_qty_secondary_unit
    if "standard_process_name" in dto.model_fields_set:
        patch["standard_process_name"] = dto.standard_process_name
    return patch


def prepare_line_fields(
    fields: BomWeldingProcessBreakdownLinePatch,
    *,
    fallback_token: str,
) -> BomWeldingProcessBreakdownLinePatch:
    """校验并补齐标准工艺/单位/map_status。"""
    if "standard_process_name" in fields:
        name = fields.get("standard_process_name")
        if name:
            if name not in _STANDARD_PROCESS_NAMES:
                raise BusinessException(f"未知标准工艺名称：{name}")
            fields["standard_process_name"] = name
            fields["map_status"] = "ready"
            fields["standard_process_unit"] = resolve_standard_process_unit(name)
        else:
            auto_name, map_status = resolve_standard_process_name(
                fields.get("process_token") or fallback_token
            )
            fields["standard_process_name"] = auto_name
            fields["map_status"] = map_status
            fields["standard_process_unit"] = resolve_standard_process_unit(auto_name)
    return fields


def update_line(
    repository: BomWeldingProcessBreakdownRepository,
    db: Session,
    line_id: int,
    dto: BomWeldingProcessBreakdownLineUpdateDTO,
    current_user: UserVO,
) -> BomWeldingProcessBreakdownLineVO:
    line = repository.get_line_by_id(db, line_id)
    if not line:
        raise NotFoundException("明细不存在")
    node = repository.get_node_by_id(db, line.breakdown_node_id)
    if not node:
        raise NotFoundException("主表不存在")
    if node.audit_status == AUDIT_APPROVED:
        raise BusinessException("已审核通过，请先反审核后再修改")

    fields = prepare_line_fields(
        line_patch_from_dto(dto),
        fallback_token=line.process_token,
    )

    need_recompute = "process_qty" in fields or "process_token" in fields
    fields["updated_by"] = audit_update(current_user)["updated_by"]
    node_patch: BomWeldingProcessBreakdownNodePatch = {"updated_by": fields["updated_by"]}
    try:
        row = repository.update_line(db, line_id, fields)
        repository.update_node(db, node.id, node_patch)
        if not row:
            db.rollback()
            raise NotFoundException("明细不存在")

        if need_recompute:
            recompute_scope_derived_fields(
                db,
                repository=repository,
                location=node.location,
                vehicle_model=node.vehicle_model,
                bom_version=resolve_breakdown_tree_root_version(db, node),
                snapshot_id=node.snapshot_id,
            )

        db.commit()
        db.refresh(row)
        return BomWeldingProcessBreakdownLineVO.model_validate(row)
    except (BusinessException, NotFoundException):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def update_node_lines(
    repository: BomWeldingProcessBreakdownRepository,
    node_repository: BomNodeRepository,
    db: Session,
    node_id: int,
    dto: BomWeldingProcessBreakdownNodeLinesUpdateDTO,
    current_user: UserVO,
) -> BomWeldingProcessBreakdownNodeVO:
    """一次保存节点下全部工艺；单事务，派生字段只重算一次。"""
    node = repository.get_node_by_id(db, node_id)
    if not node:
        raise NotFoundException("主表不存在")
    if node.audit_status == AUDIT_APPROVED:
        raise BusinessException("已审核通过，请先反审核后再修改")

    lines_by_id = {ln.id: ln for ln in (node.lines or [])}
    if not lines_by_id:
        raise BusinessException("无明细行可保存")

    seen: set[int] = set()
    need_recompute = False
    updated_by = audit_update(current_user)["updated_by"]
    audit_fields: BomWeldingProcessBreakdownNodePatch = {"updated_by": updated_by}

    try:
        for item in dto.lines:
            item_dto: BomWeldingProcessBreakdownLineBatchItemDTO = item
            if item_dto.line_id in seen:
                raise BusinessException(f"明细行重复：{item_dto.line_id}")
            seen.add(item_dto.line_id)

            line = lines_by_id.get(item_dto.line_id)
            if not line:
                raise BusinessException(f"明细不属于本节点：{item_dto.line_id}")

            fields = line_patch_from_dto(item_dto)
            if not fields:
                continue
            fields = prepare_line_fields(fields, fallback_token=line.process_token)

            if "process_qty" in fields or "process_token" in fields:
                need_recompute = True

            fields["updated_by"] = updated_by
            row = repository.update_line(db, item_dto.line_id, fields)
            if not row:
                raise NotFoundException(f"明细不存在：{item_dto.line_id}")

        repository.update_node(db, node.id, audit_fields)

        if need_recompute:
            recompute_scope_derived_fields(
                db,
                repository=repository,
                location=node.location,
                vehicle_model=node.vehicle_model,
                bom_version=resolve_breakdown_tree_root_version(db, node),
                snapshot_id=node.snapshot_id,
            )

        db.commit()
        return get_node(repository, node_repository, db, node_id)
    except (BusinessException, NotFoundException):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
