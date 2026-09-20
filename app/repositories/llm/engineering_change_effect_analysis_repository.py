"""工程变更效果链接 / 工艺布点到期 — LLM 只读。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import EFFECT_DIE_PART, EFFECT_PROCESS_PART
from app.common.period import is_in_period
from app.models.engineering_change.change_order import EngineeringChangeOrder
from app.models.engineering_change.effect_link import EngineeringChangeEffectLink
from app.models.engineering_change.upload_log import EngineeringChangeUploadLog
from app.models.stamping.die import StampingDiePart
from app.models.stamping.part import StampingPart
from app.repositories.llm.location_in import location_in_clause


@dataclass(frozen=True, slots=True)
class EngineeringChangeDownstreamRow:
    upload_log_id: int
    change_order_id: int
    location: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    change_type: str
    before_part_number: str | None
    after_part_number: str | None
    before_assembly_part_number: str
    after_assembly_part_number: str | None
    process_inserted_count: int
    die_inserted_count: int
    procurement_object_inserted_count: int
    welding_breakdown_inserted_count: int
    effect_kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProcessDiePeriodRow:
    kind: str
    part_id: int
    part_number: str
    part_name: str | None
    location: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    expiry_year: int | None
    expiry_month: int | None
    is_active_at_ec: bool
    link_id: int | None = None


class EngineeringChangeEffectAnalysisRepository:
    def query_downstream_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        start_year: int | None = None,
        start_month: int | None = None,
        end_year: int | None = None,
        end_month: int | None = None,
        limit: int = 500,
    ) -> list[EngineeringChangeDownstreamRow]:
        q = (
            db.query(EngineeringChangeOrder, EngineeringChangeUploadLog)
            .join(
                EngineeringChangeUploadLog,
                EngineeringChangeOrder.upload_log_id == EngineeringChangeUploadLog.id,
            )
            .filter(
                EngineeringChangeUploadLog.status == "success",
                EngineeringChangeOrder.status == "active",
            )
        )
        loc_filter = location_in_clause(db, EngineeringChangeUploadLog.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(EngineeringChangeUploadLog.vehicle_model == vehicle_model)
        if start_year is not None and start_month is not None:
            start_key = start_year * 12 + start_month
            q = q.filter(
                (
                    EngineeringChangeUploadLog.effective_year * 12
                    + EngineeringChangeUploadLog.effective_month
                )
                >= start_key
            )
        if end_year is not None and end_month is not None:
            end_key = end_year * 12 + end_month
            q = q.filter(
                (
                    EngineeringChangeUploadLog.effective_year * 12
                    + EngineeringChangeUploadLog.effective_month
                )
                <= end_key
            )
        q = q.order_by(
            EngineeringChangeUploadLog.effective_year.desc(),
            EngineeringChangeUploadLog.effective_month.desc(),
            EngineeringChangeOrder.id.asc(),
        ).limit(limit)
        pairs = q.all()
        if not pairs:
            return []
        order_ids = [int(order.id) for order, _log in pairs]
        links = (
            db.query(EngineeringChangeEffectLink)
            .filter(EngineeringChangeEffectLink.change_order_id.in_(order_ids))
            .all()
        )
        kinds_by_order: dict[int, list[str]] = {}
        for link in links:
            kinds_by_order.setdefault(int(link.change_order_id), []).append(str(link.effect_kind))

        rows: list[EngineeringChangeDownstreamRow] = []
        for order, log_row in pairs:
            kinds = tuple(sorted(set(kinds_by_order.get(int(order.id), []))))
            rows.append(
                EngineeringChangeDownstreamRow(
                    upload_log_id=int(log_row.id),
                    change_order_id=int(order.id),
                    location=str(log_row.location),
                    vehicle_model=str(log_row.vehicle_model),
                    effective_year=int(log_row.effective_year),
                    effective_month=int(log_row.effective_month),
                    change_type=str(order.change_type),
                    before_part_number=order.before_part_number,
                    after_part_number=order.after_part_number,
                    before_assembly_part_number=str(order.before_assembly_part_number),
                    after_assembly_part_number=order.after_assembly_part_number,
                    process_inserted_count=int(log_row.process_inserted_count or 0),
                    die_inserted_count=int(log_row.die_inserted_count or 0),
                    procurement_object_inserted_count=int(
                        log_row.procurement_object_inserted_count or 0
                    ),
                    welding_breakdown_inserted_count=int(
                        log_row.welding_breakdown_inserted_count or 0
                    ),
                    effect_kinds=kinds,
                )
            )
        return rows

    def query_process_die_period_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        start_year: int | None = None,
        start_month: int | None = None,
        end_year: int | None = None,
        end_month: int | None = None,
        limit: int = 300,
    ) -> list[ProcessDiePeriodRow]:
        """取 EC 效果链接上的工艺/布点前后实体，看相对生效月是否仍有效。"""
        q = (
            db.query(
                EngineeringChangeEffectLink,
                EngineeringChangeOrder,
                EngineeringChangeUploadLog,
            )
            .join(
                EngineeringChangeOrder,
                EngineeringChangeEffectLink.change_order_id == EngineeringChangeOrder.id,
            )
            .join(
                EngineeringChangeUploadLog,
                EngineeringChangeEffectLink.upload_log_id == EngineeringChangeUploadLog.id,
            )
            .filter(
                EngineeringChangeUploadLog.status == "success",
                EngineeringChangeOrder.status == "active",
                EngineeringChangeEffectLink.effect_kind.in_([EFFECT_PROCESS_PART, EFFECT_DIE_PART]),
            )
        )
        loc_filter = location_in_clause(db, EngineeringChangeUploadLog.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(EngineeringChangeUploadLog.vehicle_model == vehicle_model)
        if start_year is not None and start_month is not None:
            start_key = start_year * 12 + start_month
            q = q.filter(
                (
                    EngineeringChangeUploadLog.effective_year * 12
                    + EngineeringChangeUploadLog.effective_month
                )
                >= start_key
            )
        if end_year is not None and end_month is not None:
            end_key = end_year * 12 + end_month
            q = q.filter(
                (
                    EngineeringChangeUploadLog.effective_year * 12
                    + EngineeringChangeUploadLog.effective_month
                )
                <= end_key
            )
        q = q.order_by(EngineeringChangeEffectLink.id.desc()).limit(limit)
        link_rows = q.all()
        if not link_rows:
            return []

        process_ids: set[int] = set()
        die_ids: set[int] = set()
        for link, _order, _log in link_rows:
            for entity_id in (link.before_id, link.after_id):
                if entity_id is None:
                    continue
                if link.effect_kind == EFFECT_PROCESS_PART:
                    process_ids.add(int(entity_id))
                elif link.effect_kind == EFFECT_DIE_PART:
                    die_ids.add(int(entity_id))

        process_by_id = {
            int(row.id): row
            for row in db.query(StampingPart).filter(StampingPart.id.in_(process_ids or [-1])).all()
        }
        die_by_id = {
            int(row.id): row
            for row in db.query(StampingDiePart)
            .filter(StampingDiePart.id.in_(die_ids or [-1]))
            .all()
        }

        out: list[ProcessDiePeriodRow] = []
        for link, _order, log_row in link_rows:
            as_of_year = int(log_row.effective_year)
            as_of_month = int(log_row.effective_month)
            for role, entity_id in (("before", link.before_id), ("after", link.after_id)):
                if entity_id is None:
                    continue
                part: StampingPart | StampingDiePart | None
                if link.effect_kind == EFFECT_PROCESS_PART:
                    part = process_by_id.get(int(entity_id))
                    kind = f"process_{role}"
                else:
                    part = die_by_id.get(int(entity_id))
                    kind = f"die_{role}"
                if part is None:
                    continue
                active = is_in_period(
                    effective_year=int(part.effective_year),
                    effective_month=int(part.effective_month),
                    expiry_year=part.expiry_year,
                    expiry_month=part.expiry_month,
                    as_of_year=as_of_year,
                    as_of_month=as_of_month,
                )
                out.append(
                    ProcessDiePeriodRow(
                        kind=kind,
                        part_id=int(part.id),
                        part_number=str(part.part_number),
                        part_name=part.part_name,
                        location=str(part.location),
                        vehicle_model=str(part.vehicle_model),
                        effective_year=int(part.effective_year),
                        effective_month=int(part.effective_month),
                        expiry_year=part.expiry_year,
                        expiry_month=part.expiry_month,
                        is_active_at_ec=bool(active),
                        link_id=int(link.id),
                    )
                )
        return out


def build_ec_downstream_completeness(
    rows: list[EngineeringChangeDownstreamRow],
    *,
    sample_limit: int = 20,
) -> dict[str, object]:
    if not rows:
        return {
            "kind": "ec_downstream",
            "subject": "engineering_change",
            "purpose": "设变后下游写入齐套（效果链接 + 上传计数）",
            "row_count": 0,
            "message": "当前范围无工程变更记录",
        }
    kind_counter: Counter[str] = Counter()
    for row in rows:
        kind_counter.update(row.effect_kinds)
    missing_process = [
        row
        for row in rows
        if row.change_type in ("改图", "增加零件") and "process_part" not in row.effect_kinds
    ]
    has_procurement = sum(1 for row in rows if "procurement_object" in row.effect_kinds)
    upload_ids = {row.upload_log_id for row in rows}
    process_inserted = sum(
        max(row.process_inserted_count for row in rows if row.upload_log_id == uid)
        for uid in upload_ids
    )
    die_inserted = sum(
        max(row.die_inserted_count for row in rows if row.upload_log_id == uid)
        for uid in upload_ids
    )
    procurement_inserted = sum(
        max(row.procurement_object_inserted_count for row in rows if row.upload_log_id == uid)
        for uid in upload_ids
    )
    welding_inserted = sum(
        max(row.welding_breakdown_inserted_count for row in rows if row.upload_log_id == uid)
        for uid in upload_ids
    )
    samples = [
        {
            "change_type": row.change_type,
            "after_part_number": row.after_part_number,
            "before_part_number": row.before_part_number,
            "effect_kinds": list(row.effect_kinds),
            "effective_month": f"{row.effective_year}-{row.effective_month:02d}",
            "location": row.location,
            "vehicle_model": row.vehicle_model,
        }
        for row in missing_process[:sample_limit]
    ]
    return {
        "kind": "ec_downstream",
        "subject": "engineering_change",
        "purpose": "设变后下游写入齐套（效果链接 + 上传计数）",
        "row_count": len(rows),
        "upload_count": len(upload_ids),
        "effect_kind_counts": dict(sorted(kind_counter.items())),
        "process_inserted_count": process_inserted,
        "die_inserted_count": die_inserted,
        "procurement_object_inserted_count": procurement_inserted,
        "welding_breakdown_inserted_count": welding_inserted,
        "orders_with_procurement_link": has_procurement,
        "missing_process_link_count": len(missing_process),
        "missing_process_link_items": samples,
        "message": (
            f"上传 {len(upload_ids)} 本：工艺+{process_inserted}、布点+{die_inserted}、"
            f"采购对象+{procurement_inserted}、拆解+{welding_inserted}；"
            f"改图/加件缺工艺链接 {len(missing_process)} 条"
        ),
    }


def build_ec_process_die_period(
    rows: list[ProcessDiePeriodRow],
    *,
    sample_limit: int = 20,
) -> dict[str, object]:
    if not rows:
        return {
            "kind": "ec_process_die_period",
            "subject": "engineering_change",
            "purpose": "设变相关工艺/布点相对生效月是否仍有效",
            "row_count": 0,
            "message": "当前范围无工艺/布点效果链接",
        }
    expired_before = [
        row for row in rows if row.kind.endswith("_before") and not row.is_active_at_ec
    ]
    active_after = [row for row in rows if row.kind.endswith("_after") and row.is_active_at_ec]
    # 按同一效果链接的 before/after 成对看；换号后零件号不同，不能用旧号==新号判断缺布点
    die_before_rows = [row for row in rows if row.kind == "die_before"]
    die_after_link_ids = {
        row.link_id for row in rows if row.kind == "die_after" and row.link_id is not None
    }
    missing_after_die = [
        row
        for row in die_before_rows
        if row.link_id is None or row.link_id not in die_after_link_ids
    ]

    def _item(row: ProcessDiePeriodRow) -> dict[str, object]:
        return {
            "kind": row.kind,
            "part_number": row.part_number,
            "part_name": row.part_name,
            "location": row.location,
            "vehicle_model": row.vehicle_model,
            "effective_month": f"{row.effective_year}-{row.effective_month:02d}",
            "expiry_month": (
                f"{row.expiry_year}-{row.expiry_month:02d}"
                if row.expiry_year and row.expiry_month
                else None
            ),
            "is_active_at_ec": row.is_active_at_ec,
            "link_id": row.link_id,
        }

    return {
        "kind": "ec_process_die_period",
        "subject": "engineering_change",
        "purpose": "设变相关工艺/布点相对生效月是否仍有效",
        "row_count": len(rows),
        "expired_before_count": len(expired_before),
        "active_after_count": len(active_after),
        "expired_before_items": [_item(row) for row in expired_before[:sample_limit]],
        "active_after_items": [_item(row) for row in active_after[:sample_limit]],
        "die_before_without_after_count": len(missing_after_die),
        "die_before_without_after_items": [_item(row) for row in missing_after_die[:sample_limit]],
        "message": (
            f"链接实体 {len(rows)}：生效月时旧号已到期 {len(expired_before)}，"
            f"新号仍有效 {len(active_after)}"
            + (
                f"；布点有旧无新 {len(missing_after_die)} 条"
                if missing_after_die
                else "；布点未见有旧无新"
            )
        ),
    }
