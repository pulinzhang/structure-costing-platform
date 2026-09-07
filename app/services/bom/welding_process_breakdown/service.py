"""
BOM 焊接工艺拆解 — 门面 Service

对外统一入口：查询 / 修改 / 生成 / 审核。
复杂逻辑下沉到 generate / audit / rollup / fastener_check / recompute。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, audit_update, display_name
from app.common.bom.welding_standard_process import (
    all_standard_process_names,
    resolve_standard_process_name,
    resolve_standard_process_unit,
)
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom import (
    BomWeldingProcessBreakdownGenerateLog,
    BomWeldingProcessBreakdownNode,
)
from app.repositories.bom.bom_repository import BomNodeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
    WeldingBreakdownFilterSummary,
    WeldingBreakdownListFilters,
)
from app.schemas.common import DeletedCountVO
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownBatchApproveDTO,
    BomWeldingProcessBreakdownBatchReverseAuditDTO,
    BomWeldingProcessBreakdownGenerateDTO,
    BomWeldingProcessBreakdownLineBatchItemDTO,
    BomWeldingProcessBreakdownLinePatch,
    BomWeldingProcessBreakdownLineUpdateDTO,
    BomWeldingProcessBreakdownNodeLinesUpdateDTO,
    BomWeldingProcessBreakdownNodePatch,
    BomWeldingProcessBreakdownQuery,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
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
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE,
    AsyncTaskService,
    WorkerTaskOutcome,
)
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
    ProgressCallback,
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
    ) -> tuple[list[BomWeldingProcessBreakdownNodeVO], int, WeldingBreakdownListFilters]:
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
        filters: WeldingBreakdownListFilters = {
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
    ) -> WeldingBreakdownFilterSummary:
        """HUD：列表口径汇总（不含工艺数钻取）+ L0 工艺数=0（不受层级/工艺数筛选影响）。"""
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

    def get_node(self, db: Session, node_id: int) -> BomWeldingProcessBreakdownNodeVO:
        row = self.repository.get_node_by_id(db, node_id)
        if not row:
            raise NotFoundException("记录不存在")
        vo = BomWeldingProcessBreakdownNodeVO.model_validate(row)
        vo.evidence = self._build_evidence_vo(db, row)
        return vo

    def _build_evidence_vo(
        self, db: Session, row: BomWeldingProcessBreakdownNode
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
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
        started_at: datetime | None = None,
    ) -> BomWeldingProcessBreakdownGenerateResultVO:
        return self._generate_service.generate(
            db,
            dto,
            current_user,
            progress_callback=progress_callback,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
            started_at=started_at,
        )

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

    def get_generate_log(self, db: Session, log_id: int) -> BomWeldingProcessBreakdownGenerateLogVO:
        return self._generate_log_service.get_log(db, log_id)

    def delete_generate_log(self, db: Session, log_id: int) -> None:
        self._generate_log_service.delete_log(db, log_id)

    def delete_all_generate_logs(self, db: Session) -> DeletedCountVO:
        return self._generate_log_service.delete_all_logs(db)

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

    def start_generate(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownGenerateDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        bom_version = dto.bom_version.strip()
        customer_name = (dto.customer_name or "").strip() or None
        lock_log = self.begin_generate_processing(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            customer_name=customer_name,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
        log_id = lock_log.id
        calc_batch_id = lock_log.calc_batch_id
        started_at = lock_log.started_at
        scoped = BomWeldingProcessBreakdownGenerateDTO(
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            customer_name=customer_name,
        )
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE,
            message="已提交拆解队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            try:
                result = self.generate_from_bom(
                    worker_db,
                    scoped,
                    current_user,
                    progress_callback=on_progress,
                    log_id=log_id,
                    calc_batch_id=calc_batch_id,
                    started_at=started_at,
                )
            except BusinessException as exc:
                fail_message = exc.message
                return WorkerTaskOutcome(
                    status=STATUS_FAILED,
                    progress=100,
                    message=fail_message,
                    result=BomWeldingProcessBreakdownGenerateResultVO(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                        status="failed",
                        message=fail_message,
                        calc_batch_id=calc_batch_id,
                        log_id=log_id,
                        detail_text=fail_message,
                    ).model_dump(),
                )
            return WorkerTaskOutcome(
                status=STATUS_COMPLETED,
                message=result.message,
                result=result.model_dump(),
            )

        def on_crash(worker_db: Session, error: BaseException) -> None:
            self.mark_generate_log_failed(
                worker_db,
                log_id=log_id,
                message=str(error),
                detail_text=f"拆解异常: {error}",
            )

        async_task_service.submit_session_worker(
            task.task_id,
            start_message="后台开始拆解...",
            work=work,
            on_crash=on_crash,
            crash_message=lambda error: f"拆解异常: {error}",
        )
        return AsyncTaskAcceptedVO(task_id=task.task_id)

    # ---------- 修改明细（须未审核；主表来自 BOM，不可改） ----------

    def _line_patch_from_dto(
        self,
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

    def _prepare_line_fields(
        self,
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
        self,
        db: Session,
        line_id: int,
        dto: BomWeldingProcessBreakdownLineUpdateDTO,
        current_user: UserVO,
    ) -> BomWeldingProcessBreakdownLineVO:
        line = self.repository.get_line_by_id(db, line_id)
        if not line:
            raise NotFoundException("明细不存在")
        node = self.repository.get_node_by_id(db, line.breakdown_node_id)
        if not node:
            raise NotFoundException("主表不存在")
        if node.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再修改")

        fields = self._prepare_line_fields(
            self._line_patch_from_dto(dto),
            fallback_token=line.process_token,
        )

        need_recompute = "process_qty" in fields or "process_token" in fields
        fields["updated_by"] = audit_update(current_user)["updated_by"]
        node_patch: BomWeldingProcessBreakdownNodePatch = {"updated_by": fields["updated_by"]}
        try:
            row = self.repository.update_line(db, line_id, fields)
            self.repository.update_node(db, node.id, node_patch)
            if not row:
                db.rollback()
                raise NotFoundException("明细不存在")

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
            return BomWeldingProcessBreakdownLineVO.model_validate(row)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise

    def update_node_lines(
        self,
        db: Session,
        node_id: int,
        dto: BomWeldingProcessBreakdownNodeLinesUpdateDTO,
        current_user: UserVO,
    ) -> BomWeldingProcessBreakdownNodeVO:
        """一次保存节点下全部工艺；单事务，派生字段只重算一次。"""
        node = self.repository.get_node_by_id(db, node_id)
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

                fields = self._line_patch_from_dto(item_dto)
                if not fields:
                    continue
                fields = self._prepare_line_fields(fields, fallback_token=line.process_token)

                if "process_qty" in fields or "process_token" in fields:
                    need_recompute = True

                fields["updated_by"] = updated_by
                row = self.repository.update_line(db, item_dto.line_id, fields)
                if not row:
                    raise NotFoundException(f"明细不存在：{item_dto.line_id}")

            self.repository.update_node(db, node.id, audit_fields)

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
            return self.get_node(db, node_id)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
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
    ) -> BomWeldingProcessBreakdownBatchDeleteResultVO:
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
    ) -> BomWeldingProcessBreakdownBatchAuditResultVO:
        return self._audit_service.batch_approve(db, dto, current_user)

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomWeldingProcessBreakdownBatchAuditResultVO:
        return self._audit_service.batch_reverse_audit(db, dto, current_user)
