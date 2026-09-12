"""管理者作业台 summary。"""

from __future__ import annotations

from typing import Any

from app.repositories.llm.ops_workbench_repository import WorkbenchBoardRow


def build_ops_workbench_summary(boards: list[WorkbenchBoardRow]) -> dict[str, Any]:
    items = [
        {
            "slice_id": row.slice_id,
            "label": row.label,
            "hash_page": row.hash_page,
            "grain": row.grain,
            "row_count": row.row_count,
            "pending_audit_count": row.pending_audit_count,
            "incomplete_count": row.incomplete_count,
            "pending_confirm_count": row.pending_confirm_count,
        }
        for row in boards
    ]
    pending_audit_total = sum(row.pending_audit_count for row in boards)
    incomplete_total = sum(row.incomplete_count for row in boards)
    pending_confirm_total = sum(row.pending_confirm_count for row in boards)
    empty_boards = [row.label for row in boards if row.row_count == 0]
    return {
        "kind": "ops_workbench",
        "subject": "ops_workbench",
        "boards": items,
        "pending_audit_total": pending_audit_total,
        "incomplete_total": incomplete_total,
        "pending_confirm_total": pending_confirm_total,
        "empty_board_labels": empty_boards,
        "has_attention": (
            pending_audit_total > 0 or incomplete_total > 0 or pending_confirm_total > 0
        ),
    }


def build_ops_workbench_risks(summary: dict[str, Any]) -> dict[str, Any]:
    risks: list[dict[str, Any]] = []
    pending = int(summary.get("pending_audit_total") or 0)
    incomplete = int(summary.get("incomplete_total") or 0)
    confirm = int(summary.get("pending_confirm_total") or 0)
    if pending:
        risks.append(
            {
                "risk_type": "pending_audit",
                "severity": "high" if pending >= 20 else "medium",
                "count": pending,
                "message": f"有 {pending} 条结果仍待审核",
            }
        )
    if incomplete:
        risks.append(
            {
                "risk_type": "calc_incomplete",
                "severity": "high" if incomplete >= 10 else "medium",
                "count": incomplete,
                "message": f"有 {incomplete} 条核算未完成或为零价/异常区",
            }
        )
    if confirm:
        risks.append(
            {
                "risk_type": "pending_confirm",
                "severity": "medium",
                "count": confirm,
                "message": f"采购对象有 {confirm} 条尚未确认外发/自制",
            }
        )
    return {
        "kind": "risk",
        "pending_audit_count": pending,
        "incomplete_count": incomplete,
        "pending_confirm_count": confirm,
        "risks": risks,
    }
