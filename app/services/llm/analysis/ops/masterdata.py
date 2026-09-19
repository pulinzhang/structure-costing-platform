"""冲压模具费 / 检具费 / 采购对象 summary。"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from app.repositories.llm.die_fee_analysis_repository import DieFeeRow
from app.repositories.llm.gauge_fee_analysis_repository import GaugeFeeRow
from app.repositories.llm.procurement_object_analysis_repository import ProcurementObjectRow
from app.schemas.llm.analysis_payload import (
    SummaryPayload,
)
from app.services.llm._money import money_str


def build_die_fee_summary(rows: list[DieFeeRow]) -> SummaryPayload:
    if not rows:
        return {
            "subject": "stamping_die_fee",
            "row_count": 0,
            "part_count": 0,
            "pending_audit_count": 0,
            "zero_fee_count": 0,
            "years": [],
        }
    pending = sum(1 for row in rows if row.audit_status == "pending")
    zero = sum(1 for row in rows if row.final_die_fee <= 0)
    return {
        "subject": "stamping_die_fee",
        "row_count": len(rows),
        "part_count": len({row.part_number for row in rows}),
        "pending_audit_count": pending,
        "zero_fee_count": zero,
        "years": sorted({row.year for row in rows}),
        "final_die_fee_sum": money_str(sum((row.final_die_fee for row in rows), Decimal("0"))),
    }


def build_die_fee_drilldown(
    rows: list[DieFeeRow],
    *,
    part_token: str,
    head: DieFeeRow | None = None,
) -> SummaryPayload:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的模具费记录",
            "query_token": part_token,
        }
    best = head or rows[0]
    return {
        "kind": "drilldown",
        "found": True,
        "query_token": part_token,
        "part_number": best.part_number,
        "part_name": best.part_name,
        "year": best.year,
        "final_die_fee": money_str(best.final_die_fee),
        "audit_status": best.audit_status,
        "items": [
            {
                "year": row.year,
                "part_number": row.part_number,
                "final_die_fee": money_str(row.final_die_fee),
                "audit_status": row.audit_status,
            }
            for row in rows[:20]
        ],
    }


def build_gauge_fee_summary(rows: list[GaugeFeeRow]) -> SummaryPayload:
    if not rows:
        return {
            "subject": "stamping_gauge_fee",
            "row_count": 0,
            "part_count": 0,
            "effective_count": 0,
            "invalid_count": 0,
        }
    effective = sum(1 for row in rows if row.status == "effective")
    return {
        "subject": "stamping_gauge_fee",
        "row_count": len(rows),
        "part_count": len({row.part_number for row in rows}),
        "effective_count": effective,
        "invalid_count": len(rows) - effective,
        "zero_fee_count": sum(1 for row in rows if row.gauge_fee <= 0),
    }


def build_gauge_fee_drilldown(
    rows: list[GaugeFeeRow],
    *,
    part_token: str,
    head: GaugeFeeRow | None = None,
) -> SummaryPayload:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的检具费档案",
            "query_token": part_token,
        }
    best = head or rows[0]
    return {
        "kind": "drilldown",
        "found": True,
        "query_token": part_token,
        "part_number": best.part_number,
        "part_name": best.part_name,
        "gauge_fee": str(best.gauge_fee),
        "allocation_qty": str(best.allocation_qty),
        "status": best.status,
    }


def build_procurement_object_summary(rows: list[ProcurementObjectRow]) -> SummaryPayload:
    if not rows:
        return {
            "subject": "procurement_object",
            "row_count": 0,
            "pending_confirm_count": 0,
            "pending_audit_count": 0,
            "anomaly_count": 0,
            "confirm_counts": {},
        }
    confirm_counts = Counter(row.confirm_status for row in rows)
    return {
        "subject": "procurement_object",
        "row_count": len(rows),
        "part_count": len({row.part_number for row in rows}),
        "pending_confirm_count": confirm_counts.get("pending", 0),
        "outsourced_count": confirm_counts.get("outsourced", 0),
        "in_house_count": confirm_counts.get("in_house", 0),
        "pending_audit_count": sum(1 for row in rows if row.audit_status == "pending"),
        "anomaly_count": sum(1 for row in rows if row.section == "anomaly"),
        "missing_supplier_count": sum(
            1
            for row in rows
            if row.confirm_status == "outsourced" and not (row.supplier_name or "").strip()
        ),
        "confirm_counts": dict(confirm_counts),
    }


def build_procurement_object_drilldown(
    rows: list[ProcurementObjectRow],
    *,
    part_token: str,
    head: ProcurementObjectRow | None = None,
) -> SummaryPayload:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的采购对象",
            "query_token": part_token,
        }
    best = head or rows[0]
    return {
        "kind": "drilldown",
        "found": True,
        "query_token": part_token,
        "part_number": best.part_number,
        "part_name": best.part_name,
        "section": best.section,
        "confirm_status": best.confirm_status,
        "audit_status": best.audit_status,
        "supplier_name": best.supplier_name,
        "vehicle_model": best.vehicle_model,
        "bom_version": best.bom_version,
    }
