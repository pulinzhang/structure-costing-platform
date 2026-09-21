"""财务导出：对照上游 BOM L0 序号全集，标出本表缺号。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.period import period
from app.models.bom.node import BomNode
from app.models.costing.assembly_cost import AssemblyCost
from app.services.masterdata.location.service import LocationService


@dataclass(frozen=True, slots=True)
class MissingL0Seq:
    seq_no: int
    part_number: str


def find_missing_l0_seqs(
    db: Session,
    records: list[AssemblyCost],
    *,
    year: int | None,
    month: int | None,
    location: str | None,
    vehicle_model: str | None,
    part_number: str | None = None,
    audit_status: str | None = None,
    calc_status: str | None = None,
    export_seq_nos: dict[int, int | None] | None = None,
) -> tuple[list[MissingL0Seq], int | None]:
    """BOM L0（该月前已引入）= 序号全集；返回本表缺号与全集最大序号。

    有零件号/审核/核算等收窄筛选时不做对照，避免误报。
    """
    if year is None or month is None:
        return [], None
    location_raw = (location or "").strip()
    vehicle = (vehicle_model or "").strip()
    if not location_raw or not vehicle:
        return [], None
    if (part_number or "").strip() or (audit_status or "").strip() or (calc_status or "").strip():
        return [], None

    locations = LocationService().expand_for_query(db, location_raw)
    if not locations:
        return [], None
    rows = (
        db.query(BomNode)
        .filter(
            BomNode.level == 0,
            BomNode.location.in_(locations),
            BomNode.vehicle_model == vehicle,
            BomNode.seq_no.isnot(None),
        )
        .all()
    )
    as_of = period(int(year), int(month))
    introduced = [
        node
        for node in rows
        if period(int(node.effective_year), int(node.effective_month)) <= as_of
    ]
    if not introduced:
        return [], None

    part_by_seq: dict[int, str] = {}
    for node in introduced:
        seq_no = int(node.seq_no)  # type: ignore[arg-type]
        part = (node.part_number or "").strip()
        # 同序号多节点（改图换号）时，后写入的覆盖；缺号场景通常只剩已停旧号。
        if seq_no not in part_by_seq or part:
            part_by_seq[seq_no] = part

    export_seqs = _export_seq_set(records, export_seq_nos)
    universe_max = max(part_by_seq)
    missing = [
        MissingL0Seq(seq_no=seq_no, part_number=part_by_seq.get(seq_no, ""))
        for seq_no in sorted(part_by_seq)
        if seq_no not in export_seqs
    ]
    return missing, universe_max


def format_missing_l0_seq_note(
    missing: Sequence[MissingL0Seq],
    *,
    export_count: int,
    universe_max_seq: int | None,
    limit: int = 20,
) -> str:
    if not missing or universe_max_seq is None:
        return ""
    bits: list[str] = []
    for item in missing[:limit]:
        if item.part_number:
            bits.append(f"{item.seq_no}（{item.part_number}）")
        else:
            bits.append(str(item.seq_no))
    head = "、".join(bits)
    more = f" 等共 {len(missing)} 个" if len(missing) > limit else ""
    return (
        f"缺序号 {head}{more}。"
        f"本表共 {export_count} 条，勿按最大序号 {universe_max_seq} 当作件数。"
    )


def _export_seq_set(
    records: list[AssemblyCost],
    export_seq_nos: dict[int, int | None] | None,
) -> set[int]:
    result: set[int] = set()
    seq_map = export_seq_nos or {}
    for record in records:
        source_node_id = getattr(record, "source_node_id", None)
        if source_node_id is None:
            continue
        mapped = seq_map.get(int(source_node_id))
        if mapped is not None:
            result.add(int(mapped))
    return result
