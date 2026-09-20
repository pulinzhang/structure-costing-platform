"""引擎 Run 摘要：步骤计数与终态。"""

from __future__ import annotations

from app.common.types.repository_types import (
    EngineCountsJson,
    EngineStepSummaryJson,
    SummaryJson,
)
from app.services.costing.engine.scope.discovery import DiscoveryResult


def step_summary(
    stage: str, scope_key: str, status: str, message: str | None
) -> EngineStepSummaryJson:
    return {
        "stage": stage,
        "scope_key": scope_key,
        "status": status,
        "message": message,
    }


def resolve_run_status(steps: list[EngineStepSummaryJson]) -> str:
    statuses = [s.get("status") or "" for s in steps]
    has_success = any(s in ("succeeded", "skipped") for s in statuses)
    has_failed = any(s == "failed" for s in statuses)
    if has_failed and has_success:
        return "partial"
    if has_failed and not has_success:
        return "failed"
    return "succeeded"


def build_summary(
    discovery: DiscoveryResult,
    steps: list[EngineStepSummaryJson],
    *,
    run_status: str,
) -> SummaryJson:
    succeeded = 0
    failed = 0
    skipped = 0
    for step in steps:
        key = step.get("status")
        if key == "succeeded":
            succeeded += 1
        elif key == "failed":
            failed += 1
        elif key == "skipped":
            skipped += 1
    counts: EngineCountsJson = {
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
    }
    return {
        "status": run_status,
        "location": discovery.location,
        "year": discovery.year,
        "month": discovery.month,
        "steps": steps,
        "counts": counts,
    }
