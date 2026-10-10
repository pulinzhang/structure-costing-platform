"""
焊接工艺拆解旁证核对（只读计算，不改主表过程量）

链：
  A. 本节点 ↔ 直接子件紧固件用量（凸焊/植焊/铆接）
  B. L0 ↔ Σ(L1.process_qty × L1.assembly_qty)
  C. L0 ↔ Σ(L1 下 L2 紧固件用量 × L1.assembly_qty)（仅紧固件类工艺）
"""

from __future__ import annotations

from decimal import Decimal

from app.models.bom import BomNode, BomWeldingProcessBreakdownNode
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    WeldingEvidenceContribVO,
    WeldingEvidenceItemVO,
    WeldingNodeEvidenceVO,
)
from app.services.bom.welding_process_breakdown.fastener_check import (
    CHECKABLE_TOKENS,
    sum_child_fastener_qty,
)

_ZERO = Decimal("0")


def _dec(value: object | None) -> Decimal:
    if value is None:
        return _ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _fmt(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _delta_phrase(source: Decimal, evidence: Decimal) -> str:
    delta = source - evidence
    if delta == 0:
        return "差额=0"
    sign = "+" if delta > 0 else ""
    side = "原文偏大" if delta > 0 else "原文偏小"
    return f"差额={sign}{_fmt(delta)}（{side}）"


def build_node_evidence(
    node: BomWeldingProcessBreakdownNode,
    *,
    scope_nodes: list[BomWeldingProcessBreakdownNode],
    children_map: dict[int | None, list[BomNode]] | None = None,
) -> WeldingNodeEvidenceVO:
    """
    为单个拆解主表组装旁证。

    scope_nodes：同 location/vehicle_model/bom_version 下全部拆解主表（含 lines）。
    children_map：可选 BOM 邻接；缺省时不做 L2 路径旁证。
    """
    children_map = children_map or {}
    source_by_bom_id: dict[int, BomWeldingProcessBreakdownNode] = {}
    for scope_node in scope_nodes:
        if scope_node.source_node_id is not None:
            source_by_bom_id[scope_node.source_node_id] = scope_node

    items_by_token: dict[str, WeldingEvidenceItemVO] = {}

    def ensure_item(token: str) -> WeldingEvidenceItemVO:
        item = items_by_token.get(token)
        if item is None:
            item = WeldingEvidenceItemVO(process_token=token)
            items_by_token[token] = item
        return item

    # —— 链 A：本节点明细 vs 直接子件（已落库字段，补差额说明）——
    for line in node.lines or []:
        token = line.process_token
        item = ensure_item(token)
        qty = _dec(line.process_qty)
        item.source_process_qty = qty

        status = line.qty_check_status or "skipped"
        fastener_sum = (
            _dec(line.child_fastener_qty_sum) if line.child_fastener_qty_sum is not None else None
        )
        item.child_status = status
        item.child_fastener_sum = fastener_sum

        if status == "match" and fastener_sum is not None:
            item.child_delta = _ZERO
            item.child_detail = (
                f"单件过程量={_fmt(qty)}，子件紧固件合计={_fmt(fastener_sum)}，"
                f"{_delta_phrase(qty, fastener_sum)}"
                + (f"；{line.qty_check_detail}" if line.qty_check_detail else "")
            )
        elif status == "mismatch" and fastener_sum is not None:
            item.child_delta = qty - fastener_sum
            item.child_detail = (
                f"单件过程量={_fmt(qty)}，子件紧固件合计={_fmt(fastener_sum)}，"
                f"{_delta_phrase(qty, fastener_sum)}"
                + (f"；{line.qty_check_detail}" if line.qty_check_detail else "")
            )
        elif status == "no_child":
            item.child_detail = "无可对照的直接子件紧固件用量"
        elif status == "skipped":
            item.child_detail = "本工艺不做子件紧固件旁证"
        else:
            item.child_detail = line.qty_check_detail

    # —— 链 B / C：仅 L0 ——
    if node.level == 0 and node.source_node_id is not None:
        child_boms = children_map.get(node.source_node_id, [])
        # 也覆盖「仅 L1 有、L0 无」的 token
        for child_bom in child_boms:
            child_bd = source_by_bom_id.get(child_bom.id)
            if not child_bd:
                continue
            for line in child_bd.lines or []:
                ensure_item(line.process_token)

        for token, item in items_by_token.items():
            _fill_l1_rollup(
                item,
                token=token,
                parent_qty=item.source_process_qty,
                child_boms=child_boms,
                source_by_bom_id=source_by_bom_id,
            )
            if token in CHECKABLE_TOKENS:
                _fill_l2_path(
                    item,
                    token=token,
                    parent_qty=item.source_process_qty,
                    child_boms=child_boms,
                    children_map=children_map,
                    source_by_bom_id=source_by_bom_id,
                )
            else:
                item.l2_status = "skipped"
                item.l2_detail = "本工艺无 L2 紧固件路径旁证"

    mismatch_count = 0
    for item in items_by_token.values():
        if (
            item.child_status == "mismatch"
            or item.l1_status == "mismatch"
            or item.l2_status == "mismatch"
        ):
            mismatch_count += 1

    ordered = sorted(items_by_token.values(), key=lambda row: row.process_token)
    if not ordered:
        summary = "无工艺明细，无需旁证"
    elif mismatch_count:
        summary = f"{mismatch_count} 项存在差额，请核对原文或结构用量"
    else:
        summary = "旁证一致（或无可比对旁证）"

    return WeldingNodeEvidenceVO(
        level=node.level,
        summary=summary,
        has_mismatch=mismatch_count > 0,
        items=ordered,
    )


def _fill_l1_rollup(
    item: WeldingEvidenceItemVO,
    *,
    token: str,
    parent_qty: Decimal | None,
    child_boms: list[BomNode],
    source_by_bom_id: dict[int, BomWeldingProcessBreakdownNode],
) -> None:
    contribs: list[WeldingEvidenceContribVO] = []
    total = _ZERO
    for child_bom in child_boms:
        child_bd = source_by_bom_id.get(child_bom.id)
        if not child_bd:
            continue
        assembly_qty = _dec(child_bd.assembly_qty)
        for line in child_bd.lines or []:
            if line.process_token != token:
                continue
            process_qty = _dec(line.process_qty)
            contrib = process_qty * assembly_qty
            total += contrib
            contribs.append(
                WeldingEvidenceContribVO(
                    part_number=child_bd.part_number,
                    part_name=child_bd.part_name,
                    assembly_qty=assembly_qty,
                    process_qty=process_qty,
                    contrib=contrib,
                    rollup_flag=line.rollup_flag,
                )
            )

    item.l1_contribs = contribs
    item.l1_rollup_sum = total if contribs else None

    if parent_qty is None and not contribs:
        item.l1_status = "no_child"
        item.l1_detail = "L0 无此工艺，且下级无同名工艺"
        return
    if parent_qty is None and contribs:
        item.l1_status = "orphan_only"
        item.l1_delta = None
        parts = "；".join(
            f"{contrib.part_number}×{_fmt(contrib.process_qty)}×{_fmt(contrib.assembly_qty)}"
            f"={_fmt(contrib.contrib)}"
            for contrib in contribs
        )
        item.l1_detail = f"L0 原文无「{token}」，L1 滚乘合计={_fmt(total)}（{parts}）"
        return
    if parent_qty is not None and not contribs:
        item.l1_status = "l0_only"
        item.l1_rollup_sum = _ZERO
        item.l1_delta = parent_qty
        item.l1_detail = (
            f"L0={_fmt(parent_qty)}，下级无同名工艺滚乘，"
            f"{_delta_phrase(parent_qty, _ZERO)}；可能为总成独有项或手填未拆到 L1"
        )
        return

    assert parent_qty is not None
    delta = parent_qty - total
    item.l1_delta = delta
    parts = "；".join(
        f"{contrib.part_number}×{_fmt(contrib.process_qty)}×{_fmt(contrib.assembly_qty)}"
        f"={_fmt(contrib.contrib)}"
        for contrib in contribs
    )
    if delta == 0:
        item.l1_status = "match"
        item.l1_detail = (
            f"L0={_fmt(parent_qty)}，L1 滚乘合计={_fmt(total)}，"
            f"{_delta_phrase(parent_qty, total)}；{parts}"
        )
    else:
        item.l1_status = "mismatch"
        item.l1_detail = (
            f"L0={_fmt(parent_qty)}，L1 滚乘合计={_fmt(total)}，"
            f"{_delta_phrase(parent_qty, total)}；{parts}"
        )


def _fill_l2_path(
    item: WeldingEvidenceItemVO,
    *,
    token: str,
    parent_qty: Decimal | None,
    child_boms: list[BomNode],
    children_map: dict[int | None, list[BomNode]],
    source_by_bom_id: dict[int, BomWeldingProcessBreakdownNode],
) -> None:
    """L2 紧固件路径：Σ(L1 下紧固件用量 × L1.assembly_qty)。"""
    parts: list[str] = []
    total = _ZERO
    for child_bom in child_boms:
        child_bd = source_by_bom_id.get(child_bom.id)
        assembly_qty = (
            _dec(child_bd.assembly_qty)
            if child_bd is not None
            else (_dec(child_bom.qty) if child_bom.qty is not None else Decimal("1"))
        )
        # 优先用 L1 明细上已算的 child_fastener_qty_sum（同 token）
        fastener_sum: Decimal | None = None
        if child_bd is not None:
            for line in child_bd.lines or []:
                if line.process_token == token and line.child_fastener_qty_sum is not None:
                    fastener_sum = _dec(line.child_fastener_qty_sum)
                    break
        if fastener_sum is None:
            grandchildren = children_map.get(child_bom.id, [])
            fastener_sum, detail = sum_child_fastener_qty(grandchildren)
            if fastener_sum is None:
                continue
            label = detail or ""
        else:
            label = f"明细旁证={_fmt(fastener_sum)}"

        if fastener_sum <= 0:
            continue
        contrib = fastener_sum * assembly_qty
        total += contrib
        pn = child_bd.part_number if child_bd is not None else child_bom.part_number
        parts.append(
            f"{pn} 紧固件{_fmt(fastener_sum)}×装配{_fmt(assembly_qty)}={_fmt(contrib)}"
            + (f"（{label}）" if label else "")
        )

    if not parts:
        item.l2_status = "no_child"
        item.l2_path_sum = None
        item.l2_detail = "下级无可汇总的 L2 紧固件用量"
        return

    item.l2_path_sum = total
    joined = "；".join(parts)
    if parent_qty is None:
        item.l2_status = "orphan_only"
        item.l2_detail = f"L0 无「{token}」，L2 路径旁证合计={_fmt(total)}；{joined}"
        return

    delta = parent_qty - total
    item.l2_delta = delta
    if delta == 0:
        item.l2_status = "match"
    else:
        item.l2_status = "mismatch"
    item.l2_detail = (
        f"L0={_fmt(parent_qty)}，L2 路径旁证合计={_fmt(total)}，"
        f"{_delta_phrase(parent_qty, total)}；{joined}"
    )
