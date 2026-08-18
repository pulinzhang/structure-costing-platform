"""
BOM 焊接工艺拆解 — 门面 Service

对外统一入口：查询 / 修改 / 生成 / 审核。
复杂逻辑下沉到 generate / audit / rollup / fastener_check / recompute。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, audit_update
from app.common.bom.welding_standard_process import (
    all_standard_process_names,
    resolve_standard_process_name,
    resolve_standard_process_unit,
)
from app.models.bom_welding_process_breakdown_generate_log import (
    BomWeldingProcessBreakdownGenerateLog,
)
from app.repositories.bom.bom_repository import BomNodeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownBatchApproveDTO,
    BomWeldingProcessBreakdownBatchReverseAuditDTO,
    BomWeldingProcessBreakdownGenerateDTO,
    BomWeldingProcessBreakdownLineBatchItemDTO,
    BomWeldingProcessBreakdownLineUpdateDTO,
    BomWeldingProcessBreakdownNodeLinesUpdateDTO,
    BomWeldingProcessBreakdownQuery,
)
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    BomWeldingProcessBreakdownBatchAuditResultVO,
    BomWeldingProcessBreakdownBatchDeleteResultVO,
    BomWeldingProcessBreakdownGenerateLogVO,
    BomWeldingProcessBreakdownGeneratePrepStatsVO,
    BomWeldingProcessBreakdownGenerateResultVO,
    BomWeldingProcessBreakdownLineVO,
    BomWeldingProcessBreakdownNodeVO,
    WeldingNodeEvidenceVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_process_breakdown.audit_service import (
    BomWeldingProcessBreakdownAuditService,
)
from app.services.bom.welding_process_breakdown.bom_tree import build_children_map
from app.services.bom.welding_process_breakdown.evidence import build_node_evidence
from app.services.bom.welding_process_breakdown.generate_log_service import (
    BomWeldingProcessBreakdownGenerateLogService,
)
from app.services.bom.welding_process_breakdown.generate_service import (
    BomWeldingProcessBreakdownGenerateService,
)
from app.services.bom.welding_process_breakdown.recompute import (
    recompute_scope_derived_fields,
)

_STANDARD_PROCESS_NAMES = frozenset(all_standard_process_names())


class BomWeldingProcessBreakdownService:
    """焊接工艺拆解门面（Router 只依赖本类）"""

    def __init__(self) -> None:
        self.repository = BomWeldingProcessBreakdownRepository()
        self.node_repository = BomNodeRepository()
        self._generate_service = BomWeldingProcessBreakdownGenerateService()
        self._generate_log_service = BomWeldingProcessBreakdownGenerateLogService()
        self._audit_service = BomWeldingProcessBreakdownAuditService()

    # ---------- 查询 ----------

    def paginate(
        self, db: Session, query: BomWeldingProcessBreakdownQuery
    ) -> tuple[list[BomWeldingProcessBreakdownNodeVO], int, dict[str, Any]]:
        skip = (query.page - 1) * query.size
        audit_status = query.audit_status.strip() if query.audit_status else None
        rows, total = self.repository.paginate(
            db,
            location=query.location,
            customer_name=query.customer_name,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            part_number=query.part_number,
            level=query.level,
            audit_status=audit_status,
            parse_status=query.parse_status,
            process_line_count_eq=query.process_line_count_eq,
            skip=skip,
            limit=query.size,
        )
        filters = {
            "locations": self.repository.get_distinct_locations(db),
            "customer_names": self.repository.get_distinct_customer_names(db),
            "vehicle_models": self.repository.get_distinct_vehicle_models(db),
            "bom_versions": self.repository.get_distinct_bom_versions(
                db,
                location=query.location,
                vehicle_model=query.vehicle_model,
            ),
            "standard_process_names": all_standard_process_names(),
            "audit_status": audit_status,
            "summary": self._build_list_summary(
                db,
                location=query.location,
                customer_name=query.customer_name,
                vehicle_model=query.vehicle_model,
                bom_version=query.bom_version,
                part_number=query.part_number,
                level=query.level,
                audit_status=audit_status,
                parse_status=query.parse_status,
                process_line_count_eq=query.process_line_count_eq,
            ),
        }
        return (
            [BomWeldingProcessBreakdownNodeVO.model_validate(r) for r in rows],
            total,
            filters,
        )

    def _build_list_summary(
        self,
        db: Session,
        *,
        location: str | None,
        customer_name: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        part_number: str | None,
        level: int | None,
        audit_status: str | None,
        parse_status: str | None,
        process_line_count_eq: int | None,
    ) -> dict[str, Any]:
        """HUD：列表口径汇总 + L0 工艺数=0（不受 level/工艺数筛选影响）。"""
        summary = self.repository.summarize_by_filters(
            db,
            location=location,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
        )
        summary["l0_zero_process_count"] = self.repository.count_by_filters(
            db,
            location=location,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=0,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=0,
        )
        return summary

    def get_node(
        self, db: Session, node_id: int
    ) -> BomWeldingProcessBreakdownNodeVO | None:
        row = self.repository.get_node_by_id(db, node_id)
        if not row:
            return None
        vo = BomWeldingProcessBreakdownNodeVO.model_validate(row)
        vo.evidence = self._build_evidence_vo(db, row)
        return vo

    def _build_evidence_vo(
        self, db: Session, row: Any
    ) -> WeldingNodeEvidenceVO:
        scope_nodes = self.repository.list_by_scope(
            db,
            location=row.location,
            vehicle_model=row.vehicle_model,
            bom_version=row.bom_version,
        )
        children_map = None
        if row.snapshot_id is not None:
            bom_nodes = self.node_repository.list_by_snapshot(db, row.snapshot_id)
            children_map = build_children_map(bom_nodes)
        payload = build_node_evidence(
            row,
            scope_nodes=scope_nodes,
            children_map=children_map,
        )
        return WeldingNodeEvidenceVO.model_validate(payload)

    # ---------- 生成（委托） ----------

    def get_generate_prep_stats(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomWeldingProcessBreakdownGeneratePrepStatsVO:
        return self._generate_service.get_prep_stats(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def generate_from_bom(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownGenerateDTO,
        current_user: UserVO,
        **kwargs: Any,
    ) -> tuple[BomWeldingProcessBreakdownGenerateResultVO | None, str | None]:
        return self._generate_service.generate(db, dto, current_user, **kwargs)

    def begin_generate_processing(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        customer_name: str | None = None,
        operator_id: int | None = None,
        operator_name: str | None = None,
    ) -> BomWeldingProcessBreakdownGenerateLog:
        return self._generate_log_service.begin_processing(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            customer_name=customer_name,
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def list_generate_logs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[BomWeldingProcessBreakdownGenerateLogVO], int]:
        return self._generate_log_service.list_logs(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            page=page,
            size=size,
        )

    def get_generate_log(
        self, db: Session, log_id: int
    ) -> BomWeldingProcessBreakdownGenerateLogVO | None:
        return self._generate_log_service.get_log(db, log_id)

    def delete_generate_log(self, db: Session, log_id: int) -> bool:
        return self._generate_log_service.delete_log(db, log_id)

    def mark_generate_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        message: str,
        detail_text: str | None = None,
    ) -> None:
        self._generate_service.mark_log_failed(
            db, log_id=log_id, message=message, detail_text=detail_text
        )

    # ---------- 修改明细（须未审核；主表来自 BOM，不可改） ----------

    def _prepare_line_fields(
        self,
        fields: dict[str, Any],
        *,
        fallback_token: str,
    ) -> tuple[dict[str, Any], str | None]:
        """校验并补齐标准工艺/单位/map_status；失败返回 (payload, error)。"""
        if "standard_process_name" in fields:
            name = fields.get("standard_process_name")
            if name:
                if name not in _STANDARD_PROCESS_NAMES:
                    return fields, f"未知标准工艺名称：{name}"
                fields["standard_process_name"] = name
                fields["map_status"] = "ready"
                fields["standard_process_unit"] = resolve_standard_process_unit(name)
            else:
                auto_name, map_status = resolve_standard_process_name(
                    fields.get("process_token") or fallback_token
                )
                fields["standard_process_name"] = auto_name
                fields["map_status"] = map_status
                fields["standard_process_unit"] = resolve_standard_process_unit(
                    auto_name
                )
        return fields, None

    def update_line(
        self,
        db: Session,
        line_id: int,
        dto: BomWeldingProcessBreakdownLineUpdateDTO,
        current_user: UserVO,
    ) -> tuple[BomWeldingProcessBreakdownLineVO | None, str | None]:
        line = self.repository.get_line_by_id(db, line_id)
        if not line:
            return None, "明细不存在"
        node = self.repository.get_node_by_id(db, line.breakdown_node_id)
        if not node:
            return None, "主表不存在"
        if node.audit_status == AUDIT_APPROVED:
            return None, "已审核通过，请先反审核后再修改"

        fields = dto.model_dump(exclude_unset=True)
        fields, err = self._prepare_line_fields(
            fields, fallback_token=line.process_token
        )
        if err:
            return None, err

        need_recompute = "process_qty" in fields or "process_token" in fields
        payload = {**fields, **audit_update(current_user)}
        try:
            row = self.repository.update_line(db, line_id, payload, commit=False)
            self.repository.update_node(
                db, node.id, audit_update(current_user), commit=False
            )
            if not row:
                db.rollback()
                return None, "明细不存在"

            if need_recompute:
                recompute_scope_derived_fields(
                    db,
                    repository=self.repository,
                    location=node.location,
                    vehicle_model=node.vehicle_model,
                    bom_version=node.bom_version,
                    snapshot_id=node.snapshot_id,
                )

            db.commit()
            db.refresh(row)
            return BomWeldingProcessBreakdownLineVO.model_validate(row), None
        except Exception:
            db.rollback()
            raise

    def update_node_lines(
        self,
        db: Session,
        node_id: int,
        dto: BomWeldingProcessBreakdownNodeLinesUpdateDTO,
        current_user: UserVO,
    ) -> tuple[BomWeldingProcessBreakdownNodeVO | None, str | None]:
        """一次保存节点下全部工艺；单事务，派生字段只重算一次。"""
        node = self.repository.get_node_by_id(db, node_id)
        if not node:
            return None, "主表不存在"
        if node.audit_status == AUDIT_APPROVED:
            return None, "已审核通过，请先反审核后再修改"

        lines_by_id = {ln.id: ln for ln in (node.lines or [])}
        if not lines_by_id:
            return None, "无明细行可保存"

        seen: set[int] = set()
        need_recompute = False
        audit_fields = audit_update(current_user)

        try:
            for item in dto.lines:
                item_dto: BomWeldingProcessBreakdownLineBatchItemDTO = item
                if item_dto.line_id in seen:
                    db.rollback()
                    return None, f"明细行重复：{item_dto.line_id}"
                seen.add(item_dto.line_id)

                line = lines_by_id.get(item_dto.line_id)
                if not line:
                    db.rollback()
                    return None, f"明细不属于本节点：{item_dto.line_id}"

                fields = item_dto.model_dump(exclude_unset=True, exclude={"line_id"})
                if not fields:
                    continue
                fields, err = self._prepare_line_fields(
                    fields, fallback_token=line.process_token
                )
                if err:
                    db.rollback()
                    return None, err

                if "process_qty" in fields or "process_token" in fields:
                    need_recompute = True

                payload = {**fields, **audit_fields}
                row = self.repository.update_line(
                    db, item_dto.line_id, payload, commit=False
                )
                if not row:
                    db.rollback()
                    return None, f"明细不存在：{item_dto.line_id}"

            self.repository.update_node(db, node.id, audit_fields, commit=False)

            if need_recompute:
                recompute_scope_derived_fields(
                    db,
                    repository=self.repository,
                    location=node.location,
                    vehicle_model=node.vehicle_model,
                    bom_version=node.bom_version,
                    snapshot_id=node.snapshot_id,
                )

            db.commit()
            return self.get_node(db, node_id), None
        except Exception:
            db.rollback()
            raise

    # ---------- 审核流（委托） ----------

    def batch_delete(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> tuple[BomWeldingProcessBreakdownBatchDeleteResultVO | None, str | None]:
        return self._audit_service.batch_delete(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def batch_approve(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownBatchApproveDTO,
        current_user: UserVO,
    ) -> tuple[BomWeldingProcessBreakdownBatchAuditResultVO | None, str | None]:
        return self._audit_service.batch_approve(db, dto, current_user)

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> tuple[BomWeldingProcessBreakdownBatchAuditResultVO | None, str | None]:
        return self._audit_service.batch_reverse_audit(db, dto, current_user)
