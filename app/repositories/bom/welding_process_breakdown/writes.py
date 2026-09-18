"""焊接工艺拆解写入：节点/明细增改、按范围删未审、审核/反审。"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom import (
    BomWeldingProcessBreakdownLine,
    BomWeldingProcessBreakdownNode,
)
from app.repositories.bom.welding_process_breakdown.queries import WeldingBreakdownQueries
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownLinePatch,
    BomWeldingProcessBreakdownLineWrite,
    BomWeldingProcessBreakdownNodePatch,
    BomWeldingProcessBreakdownNodeWrite,
)

logger = logging.getLogger("repository.bom.welding_process_breakdown")


class WeldingBreakdownWrites:
    def __init__(self, queries: WeldingBreakdownQueries | None = None) -> None:
        self._queries = queries or WeldingBreakdownQueries()

    def create_node(
        self,
        db: Session,
        data: BomWeldingProcessBreakdownNodeWrite,
    ) -> BomWeldingProcessBreakdownNode:
        row = model_from_payload(BomWeldingProcessBreakdownNode, data)
        if not row.audit_status:
            row.audit_status = AUDIT_PENDING
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def create_line(
        self,
        db: Session,
        data: BomWeldingProcessBreakdownLineWrite,
    ) -> BomWeldingProcessBreakdownLine:
        row = model_from_payload(BomWeldingProcessBreakdownLine, data)
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def update_node(
        self,
        db: Session,
        node_id: int,
        update_data: BomWeldingProcessBreakdownNodePatch,
    ) -> BomWeldingProcessBreakdownNode | None:
        row = self._queries.get_node_by_id(db, node_id)
        if not row:
            return None
        apply_payload_fields(row, update_data)
        db.flush()
        db.refresh(row)
        return row

    def update_line(
        self,
        db: Session,
        line_id: int,
        update_data: BomWeldingProcessBreakdownLinePatch,
    ) -> BomWeldingProcessBreakdownLine | None:
        row = self._queries.get_line_by_id(db, line_id)
        if not row:
            return None
        apply_payload_fields(row, update_data)
        db.flush()
        db.refresh(row)
        return row

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> int:
        count = (
            db.query(BomWeldingProcessBreakdownNode)
            .filter(
                and_(
                    *self._queries._scope_filter(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                    )
                ),
                BomWeldingProcessBreakdownNode.audit_status != AUDIT_APPROVED,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info(
            "删除未审核焊接工艺拆解: %s/%s/%s count=%s",
            location,
            vehicle_model,
            bom_version,
            count,
        )
        return count

    def delete_node_by_id(self, db: Session, node_id: int) -> bool:
        """删单节点（明细 CASCADE）。只 flush。"""
        row = self._queries.get_node_by_id(db, node_id)
        if row is None:
            return False
        db.delete(row)
        db.flush()
        return True

    def approve_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
        updated_by: str | None = None,
    ) -> int:
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_APPROVED,
            "audited_by": audited_by,
            "audited_at": audited_at,
            "audit_remark": audit_remark,
            "updated_by": updated_by or audited_by,
        }
        count = query_update(
            db.query(BomWeldingProcessBreakdownNode).filter(
                and_(
                    *self._queries._scope_filter(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                    )
                ),
                BomWeldingProcessBreakdownNode.audit_status != AUDIT_APPROVED,
            ),
            values,
        )
        db.flush()
        return count

    def reverse_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str | None = None,
    ) -> int:
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_PENDING,
            "reverse_audited_by": reverse_audited_by,
            "reverse_audited_at": reverse_audited_at,
            "reverse_audit_remark": reverse_audit_remark,
            "updated_by": updated_by or reverse_audited_by,
        }
        count = query_update(
            db.query(BomWeldingProcessBreakdownNode).filter(
                and_(
                    *self._queries._scope_filter(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                    )
                ),
                BomWeldingProcessBreakdownNode.audit_status == AUDIT_APPROVED,
            ),
            values,
        )
        db.flush()
        return count
