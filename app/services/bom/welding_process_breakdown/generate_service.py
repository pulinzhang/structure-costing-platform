"""
从 BOM 生成焊接工艺拆解

职责：校验范围 → 清空未审核旧数据 → 拆解落库 → 打 rollup 标记。
支持 progress_callback / 批次日志终态（异步任务用）。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, audit_create
from app.common.timezone import now
from app.models.bom import BomNode, BomSnapshot, BomWeldingProcessBreakdownNode
from app.parsers.bom.welding_process_breakdown_parser import parse_welding_info_text
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownGenerateDTO,
    BomWeldingProcessBreakdownLineWrite,
    BomWeldingProcessBreakdownNodeWrite,
)
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    BomWeldingProcessBreakdownGeneratePrepStatsVO,
    BomWeldingProcessBreakdownGenerateResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_process_breakdown.bom_tree import (
    annotate_parse_status,
    build_children_map,
    index_nodes_by_id,
    resolve_supply_root,
)
from app.services.bom.welding_process_breakdown.fastener_check import (
    check_process_qty_against_children,
)
from app.services.bom.welding_process_breakdown.generate_log_service import (
    STATUS_SUCCESS,
    BomWeldingProcessBreakdownGenerateLogService,
)
from app.services.bom.welding_process_breakdown.process_log import ProcessLogBuilder
from app.services.bom.welding_process_breakdown.rollup import apply_rollup_flags

logger = logging.getLogger("service.bom.welding_process_breakdown.generate")

ProgressCallback = Callable[[int, str], None]


class BomWeldingProcessBreakdownGenerateService:
    """焊接工艺拆解 — 生成编排"""

    def __init__(self) -> None:
        self.repository = BomWeldingProcessBreakdownRepository()
        self.snapshot_repository = BomSnapshotRepository()
        self.node_repository = BomNodeRepository()
        self.log_service = BomWeldingProcessBreakdownGenerateLogService()

    def get_prep_stats(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomWeldingProcessBreakdownGeneratePrepStatsVO:
        location = location.strip()
        vehicle_model = vehicle_model.strip()
        bom_version = bom_version.strip()
        snapshot = self.snapshot_repository.get_by_unique_key(
            db, location, vehicle_model, bom_version
        )
        if not snapshot:
            return BomWeldingProcessBreakdownGeneratePrepStatsVO(
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                ready=False,
                message="未找到对应材料清单版本",
            )

        bom_nodes = self.node_repository.list_by_snapshot(db, snapshot.id)
        weld_node_count = sum(
            1 for n in bom_nodes if (n.weld_info or "").strip()
        )
        breakdown_node_count = self.repository.count_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        approved_count = self.repository.count_by_scope_and_statuses(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=[AUDIT_APPROVED],
        )
        ready = weld_node_count > 0 and approved_count == 0
        if approved_count > 0:
            message = f"已有 {approved_count} 条已审拆解，请先反审核"
        elif weld_node_count <= 0:
            message = "该版本无焊接原文节点"
        else:
            message = "数据就绪，可开始拆解"

        return BomWeldingProcessBreakdownGeneratePrepStatsVO(
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            snapshot_id=snapshot.id,
            customer_name=snapshot.customer_name,
            weld_node_count=weld_node_count,
            breakdown_node_count=breakdown_node_count,
            approved_count=approved_count,
            ready=ready,
            message=message,
        )

    def generate(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownGenerateDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
        started_at: datetime | None = None,
    ) -> tuple[BomWeldingProcessBreakdownGenerateResultVO | None, str | None]:
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        bom_version = dto.bom_version.strip()
        customer_name_filter = (dto.customer_name or "").strip() or None
        process_log = ProcessLogBuilder()
        started = started_at or now()

        def report(progress: int, msg: str) -> None:
            if progress_callback:
                progress_callback(progress, msg)

        process_log.section("范围")
        process_log.line(
            f"基地={location} 项目={vehicle_model} 版本={bom_version}"
            + (f" 顾客={customer_name_filter}" if customer_name_filter else "")
        )
        report(5, "解析 BOM 快照...")

        snapshot, error = self._resolve_snapshot(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            customer_name_filter=customer_name_filter,
        )
        if error or snapshot is None:
            process_log.error(error or "未找到 BOM")
            self._fail_log(
                db,
                log_id=log_id,
                message=error or "未找到 BOM",
                detail_text=process_log.build(),
            )
            return None, error

        process_log.line(
            f"snapshot_id={snapshot.id} 顾客={snapshot.customer_name or '—'}"
        )
        report(12, "检查已审核数据...")

        approved_count = self.repository.count_by_scope_and_statuses(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=[AUDIT_APPROVED],
        )
        if approved_count > 0:
            err = (
                f"该范围已有 {approved_count} 条已审核拆解，"
                "请先反审核后再重新生成"
            )
            process_log.error(err)
            self._fail_log(
                db, log_id=log_id, message=err, detail_text=process_log.build()
            )
            return None, err

        bom_nodes = self.node_repository.list_by_snapshot(db, snapshot.id)
        by_id = index_nodes_by_id(bom_nodes)
        children_map = build_children_map(bom_nodes)
        weld_candidates = [n for n in bom_nodes if (n.weld_info or "").strip()]
        process_log.line(
            f"BOM 节点 {len(bom_nodes)}，含焊接原文 {len(weld_candidates)}"
        )
        audit_fields = audit_create(current_user)

        try:
            report(20, "清理未审核旧拆解...")
            process_log.section("清理")
            deleted = self.repository.delete_unaudited_by_scope(
                db,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                commit=False,
            )
            process_log.line(f"删除未审核旧数据：{deleted} 条主表")

            created_nodes: list[BomWeldingProcessBreakdownNode] = []
            line_count = 0
            source_to_breakdown: dict[int, BomWeldingProcessBreakdownNode] = {}
            total = max(len(weld_candidates), 1)

            process_log.section("拆解")
            report(25, f"开始拆解 {len(weld_candidates)} 个节点...")

            for index, bom_node in enumerate(weld_candidates):
                weld_raw = (bom_node.weld_info or "").strip()
                breakdown_node, lines_added = self._persist_node_with_lines(
                    db,
                    snapshot=snapshot,
                    bom_node=bom_node,
                    by_id=by_id,
                    children_map=children_map,
                    weld_raw=weld_raw,
                    created_by=audit_fields["created_by"],
                    updated_by=audit_fields["updated_by"],
                )
                created_nodes.append(breakdown_node)
                source_to_breakdown[bom_node.id] = breakdown_node
                line_count += lines_added

                if index == 0 or (index + 1) % 10 == 0 or index + 1 == total:
                    pct = 25 + int(60 * (index + 1) / total)
                    report(
                        min(pct, 85),
                        f"已拆解 {index + 1}/{total} · 明细 {line_count}",
                    )

            report(88, "计算 rollup 标记...")
            process_log.line("应用父子 rollup 标记")
            apply_rollup_flags(created_nodes, source_to_breakdown, children_map)
            db.flush()
            db.commit()

            finished = now()
            message = (
                f"已生成焊接工艺拆解：主表 {len(created_nodes)} 条，"
                f"明细 {line_count} 条"
            )
            process_log.section("结果")
            process_log.line(message)

            result = BomWeldingProcessBreakdownGenerateResultVO(
                location=location,
                customer_name=snapshot.customer_name,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                snapshot_id=snapshot.id,
                node_count=len(created_nodes),
                line_count=line_count,
                message=message,
                calc_batch_id=calc_batch_id,
                log_id=log_id,
                status=STATUS_SUCCESS,
                detail_text=process_log.build(),
                started_at=started.isoformat(timespec="seconds"),
                finished_at=finished.isoformat(timespec="seconds"),
            )

            if log_id is not None:
                self.log_service.finalize(
                    db, log_id=log_id, result=result, finished_at=finished
                )
                result.log_id = log_id

            report(100, message)
            logger.info(
                "生成焊接工艺拆解: %s/%s/%s nodes=%s lines=%s",
                location,
                vehicle_model,
                bom_version,
                result.node_count,
                result.line_count,
            )
            return result, None
        except Exception as exc:
            db.rollback()
            logger.exception("生成焊接工艺拆解失败")
            process_log.error(str(exc))
            self._fail_log(
                db,
                log_id=log_id,
                message=str(exc),
                detail_text=process_log.build(),
            )
            return None, str(exc)

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        message: str,
        detail_text: str | None = None,
    ) -> None:
        self.log_service.mark_failed(
            db, log_id=log_id, message=message, detail_text=detail_text
        )

    def _fail_log(
        self,
        db: Session,
        *,
        log_id: int | None,
        message: str,
        detail_text: str,
    ) -> None:
        if log_id is None:
            return
        self.log_service.mark_failed(
            db, log_id=log_id, message=message, detail_text=detail_text
        )

    def _resolve_snapshot(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        customer_name_filter: str | None,
    ) -> tuple[BomSnapshot | None, str | None]:
        snapshot = self.snapshot_repository.get_by_unique_key(
            db, location, vehicle_model, bom_version
        )
        if not snapshot:
            return None, (
                f"未找到 BOM：基地={location} 项目={vehicle_model} 版本={bom_version}"
            )
        if customer_name_filter and (snapshot.customer_name or "") != customer_name_filter:
            return None, (
                f"顾客名称不匹配：期望「{customer_name_filter}」，"
                f"清单为「{snapshot.customer_name or ''}」"
            )
        return snapshot, None

    def _persist_node_with_lines(
        self,
        db: Session,
        *,
        snapshot: BomSnapshot,
        bom_node: BomNode,
        by_id: dict[int, BomNode],
        children_map: dict[int | None, list[BomNode]],
        weld_raw: str,
        created_by: str,
        updated_by: str,
    ) -> tuple[BomWeldingProcessBreakdownNode, int]:
        parent = by_id.get(bom_node.parent_id) if bom_node.parent_id else None
        supply = resolve_supply_root(bom_node, by_id)
        children = children_map.get(bom_node.id, [])
        assembly_qty = bom_node.qty if bom_node.qty is not None else Decimal("1")
        parse_result = parse_welding_info_text(weld_raw)
        parse_status, qa_note = annotate_parse_status(
            level=int(bom_node.level),
            has_children=bool(children),
            base_parse_status=parse_result.parse_status,
        )
        process_line_count = len(parse_result.items)

        breakdown_node = self.repository.create_node(
            db,
            BomWeldingProcessBreakdownNodeWrite(
                location=snapshot.location,
                customer_name=snapshot.customer_name,
                vehicle_model=snapshot.vehicle_model,
                bom_version=snapshot.bom_version,
                snapshot_id=snapshot.id,
                source_node_id=bom_node.id,
                part_number=bom_node.part_number,
                part_name=bom_node.part_name,
                level=int(bom_node.level),
                node_role=bom_node.node_role,
                parent_part_number=parent.part_number if parent else None,
                parent_part_name=parent.part_name if parent else None,
                supply_part_number=supply.part_number,
                supply_part_name=supply.part_name,
                assembly_qty=assembly_qty,
                assembly_qty_unit=bom_node.qty_unit,
                weld_info_raw=weld_raw,
                excel_row=bom_node.excel_row,
                parse_status=parse_status,
                process_line_count=process_line_count,
                qa_note=qa_note,
                audit_status=AUDIT_PENDING,
                created_by=created_by,
                updated_by=updated_by,
            ),
            commit=False,
        )

        for index, item in enumerate(parse_result.items, start=1):
            qty_check = check_process_qty_against_children(
                process_token=item.process_token,
                process_qty=item.process_qty,
                children=children,
            )
            self.repository.create_line(
                db,
                BomWeldingProcessBreakdownLineWrite(
                    breakdown_node_id=breakdown_node.id,
                    part_number=bom_node.part_number,
                    line_no=index,
                    process_token=item.process_token,
                    matched_span=item.matched_span,
                    process_qty=item.process_qty,
                    process_qty_unit=item.process_qty_unit,
                    process_qty_secondary=item.process_qty_secondary,
                    process_qty_secondary_unit=item.process_qty_secondary_unit,
                    standard_process_name=item.standard_process_name,
                    standard_process_unit=item.standard_process_unit,
                    map_status=item.map_status,
                    rollup_flag="own",
                    child_fastener_qty_sum=qty_check.child_fastener_qty_sum,
                    qty_check_status=qty_check.qty_check_status,
                    qty_check_detail=qty_check.qty_check_detail,
                    created_by=created_by,
                    updated_by=updated_by,
                ),
                commit=False,
            )

        return breakdown_node, process_line_count