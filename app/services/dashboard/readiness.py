"""仪表盘：就绪度与本期产出。"""

from __future__ import annotations

from app.schemas.vo.dashboard_vo import (
    DashboardAuditBucketVO,
    DashboardOutcomeVO,
    DashboardReadinessVO,
    DashboardYishiyiyiStatsVO,
)


def build_outcome(
    process_fee: DashboardAuditBucketVO,
    steel_price: DashboardAuditBucketVO,
    part_cost: DashboardAuditBucketVO,
) -> DashboardOutcomeVO:
    return DashboardOutcomeVO(
        pending_total=(
            process_fee.pending_count + steel_price.pending_count + part_cost.pending_count
        ),
        process_fee_pending=process_fee.pending_count,
        steel_price_pending=steel_price.pending_count,
        part_cost_pending=part_cost.pending_count,
        process_fee_zero=int(process_fee.zero_count or 0),
        part_cost_approved=part_cost.approved_count,
        part_cost_avg=part_cost.avg_value,
        steel_price_avg=steel_price.avg_value,
        process_fee_avg=process_fee.avg_value,
    )


def build_readiness(
    yishiyiyi: DashboardYishiyiyiStatsVO,
    process_fee: DashboardAuditBucketVO,
    steel_price: DashboardAuditBucketVO,
    part_cost: DashboardAuditBucketVO,
) -> DashboardReadinessVO:
    has_process_fee = (process_fee.total_count or 0) > 0
    has_steel = steel_price.pending_count + steel_price.approved_count > 0
    has_part = part_cost.pending_count + part_cost.approved_count > 0
    if yishiyiyi.is_scrap_location_filled is not None:
        scrap_ok = bool(yishiyiyi.is_scrap_location_filled)
    else:
        scrap_ok = yishiyiyi.is_scrap_complete
    flags = (
        yishiyiyi.base_price_count > 0,
        yishiyiyi.policy_count > 0,
        scrap_ok,
        has_process_fee,
        has_steel,
        has_part,
    )
    return DashboardReadinessVO(
        has_base_price=flags[0],
        has_policy=flags[1],
        is_scrap_complete=flags[2],
        has_process_fee=flags[3],
        has_steel_price=flags[4],
        has_part_cost=flags[5],
        ready_count=sum(1 for flag in flags if flag),
        total_count=len(flags),
    )
