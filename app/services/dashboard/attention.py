"""仪表盘：待办关注项（按严重度排序）。"""

from __future__ import annotations

from app.schemas.vo.dashboard_vo import (
    DashboardAttentionItemVO,
    DashboardAuditBucketVO,
    DashboardBomStatsVO,
    DashboardMasterStatsVO,
    DashboardYishiyiyiStatsVO,
)


def build_attention(
    *,
    master: DashboardMasterStatsVO,
    yishiyiyi: DashboardYishiyiyiStatsVO,
    process_fee: DashboardAuditBucketVO,
    steel_price: DashboardAuditBucketVO,
    part_cost: DashboardAuditBucketVO,
    bom: DashboardBomStatsVO,
) -> list[DashboardAttentionItemVO]:
    items: list[DashboardAttentionItemVO] = []

    if master.parts == 0:
        items.append(
            DashboardAttentionItemVO(
                code="master_empty",
                severity="critical",
                title="冲压主数据为空",
                detail="尚未入库工艺零件，无法开展加工费与冲压零件核价",
                page="stamping-upload",
            )
        )

    if yishiyiyi.base_price_count == 0:
        items.append(
            DashboardAttentionItemVO(
                code="base_price_missing",
                severity="critical",
                title="当期无中标基价",
                detail="钢材联动计算缺少基价依据",
                page="base-price-download",
            )
        )
    if yishiyiyi.policy_count == 0:
        items.append(
            DashboardAttentionItemVO(
                code="policy_missing",
                severity="warning",
                title="当期无加减价政策",
                detail="厚宽调价规则未入库，联动价可能不完整",
                page="steel-price-policy-download",
            )
        )
    if yishiyiyi.is_scrap_location_filled is False:
        loc_label = yishiyiyi.scrap_location or "所选基地"
        items.append(
            DashboardAttentionItemVO(
                code="scrap_incomplete",
                severity="warning",
                title=f"{loc_label}废料价未录入",
                detail="当期该基地废料净价缺失，冲压零件核价扣减可能不全",
                page="scrap-price",
            )
        )
    elif yishiyiyi.is_scrap_location_filled is None and not yishiyiyi.is_scrap_complete:
        items.append(
            DashboardAttentionItemVO(
                code="scrap_incomplete",
                severity="warning",
                title="废料月度价未齐",
                detail=(
                    f"已录 {yishiyiyi.scrap_filled_count}/"
                    f"{yishiyiyi.scrap_required_count}，冲压零件核价扣减可能不全"
                ),
                count=yishiyiyi.scrap_required_count - yishiyiyi.scrap_filled_count,
                page="scrap-price",
            )
        )

    zero = int(process_fee.zero_count or 0)
    if zero > 0:
        items.append(
            DashboardAttentionItemVO(
                code="process_fee_zero",
                severity="warning",
                title="加工费待补价",
                detail="存在零价 / 需手工补价记录，影响冲压零件核价",
                count=zero,
                page="stamping-process-fee",
            )
        )
    if process_fee.pending_count > 0:
        items.append(
            DashboardAttentionItemVO(
                code="process_fee_pending",
                severity="warning",
                title="加工费待审核",
                detail="审核通过后方可作为冲压零件核价依据",
                count=process_fee.pending_count,
                page="stamping-process-fee",
            )
        )
    if steel_price.pending_count > 0:
        items.append(
            DashboardAttentionItemVO(
                code="steel_price_pending",
                severity="warning",
                title="钢材联动价待审核",
                detail="待审联动价尚未锁定",
                count=steel_price.pending_count,
                page="steel-price-list",
            )
        )
    if part_cost.pending_count > 0:
        items.append(
            DashboardAttentionItemVO(
                code="part_cost_pending",
                severity="warning",
                title="冲压零件价格待审核",
                detail="本期冲压件核价结果等待管理者确认",
                count=part_cost.pending_count,
                page="stamping-part-cost",
            )
        )

    has_steel = steel_price.pending_count + steel_price.approved_count > 0
    has_part = part_cost.pending_count + part_cost.approved_count > 0
    if yishiyiyi.base_price_count > 0 and not has_steel:
        items.append(
            DashboardAttentionItemVO(
                code="steel_price_empty",
                severity="info",
                title="本期尚未算出钢材联动价",
                detail="基价已就绪，可发起联动计算",
                page="steel-price-calc",
            )
        )
    if (process_fee.total_count or 0) > 0 and has_steel and not has_part:
        items.append(
            DashboardAttentionItemVO(
                code="part_cost_empty",
                severity="info",
                title="本期尚未核算冲压零件价格",
                detail="加工费与钢价已有数据，可发起冲压零件核价",
                page="stamping-part-cost-calc",
            )
        )
    if bom.snapshot_count == 0:
        items.append(
            DashboardAttentionItemVO(
                code="bom_empty",
                severity="info",
                title="BOM 清单未覆盖",
                detail="材料清单版本为空，结构核对受限",
                page="bom-structure",
            )
        )

    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    items.sort(key=lambda item: (severity_rank.get(item.severity, 9), item.code))
    return items
