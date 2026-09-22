"""删零件被外键挡住之后，按加工费和零件核价的实际行拼说明。只读表名。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED

_CHUNK = 500
_PART_COST_PAGE = "核价 → 冲压零件价格核算 → 冲压零件价格一览"
_PROCESS_FEE_PAGE = "冲压工程 → 冲压加工费 → 冲压加工费列表"
_CHANGE_PAGE = "工程变更 → 工程变更单列表"

_DELETE_FILTERS = (
    "列表上的审核状态、零件号不参与批量删除；就算列表被筛成空的，也要按列出的范围点批量删除。"
    "工厂和版本没选成列出的值，对应行还在；这两项都不选，才会把该范围里各厂、各版本的未审核行一起删掉。"
)
_REVERSE = "反审核不看工厂，按整车；版本要选成列出的那一个，不选版本会反审核该范围的全部版本。"


@dataclass(frozen=True, slots=True)
class _Scope:
    location: str
    supplier: str
    vehicle_model: str
    version: str
    year: int
    month: int | None
    audit_status: str

    def label(self) -> str:
        when = f"{self.year}年{self.month:02d}月" if self.month is not None else f"{self.year}年"
        return (
            f"基地 {self.location}、工厂 {self.supplier}、"
            f"项目 {self.vehicle_model}、版本 {self.version}、{when}"
        )


def explain_part_delete_blocked(db: Session, part_ids: list[int]) -> str:
    """part_ids 是这次要删的全部零件。没有查到引用时只说这次没删成。"""
    body = _reference_text(db, part_ids, rolling_back=False)
    return body or "这次没有删成。"


def explain_part_rollback_blocked(db: Session, part_ids: list[int]) -> str:
    """回滚要删的新零件。没有加工费或零件核价时返回空串。"""
    return _reference_text(db, part_ids, rolling_back=True)


def _reference_text(db: Session, part_ids: list[int], *, rolling_back: bool) -> str:
    costs = _cost_scopes(db, part_ids)
    fees = _fee_scopes(db, part_ids)
    pieces: list[str] = []
    if costs:
        pieces.append(_part_cost_text(costs, rolling_back=rolling_back))
    if fees:
        pieces.append(_process_fee_text(fees, rolling_back=rolling_back))
    return "".join(pieces)


def _part_cost_text(rows: list[_Scope], *, rolling_back: bool) -> str:
    return _blocked_text(
        rows,
        label="冲压零件价格",
        page=_PART_COST_PAGE,
        unaudited_note="待审和已驳回会一起删掉",
        rolling_back=rolling_back,
        done="处理完再回到这里删零件。",
    )


def _process_fee_text(rows: list[_Scope], *, rolling_back: bool) -> str:
    return _blocked_text(
        rows,
        label="冲压加工费",
        page=_PROCESS_FEE_PAGE,
        unaudited_note="按年，待审和已驳回会一起删掉",
        rolling_back=rolling_back,
        done="删完再回来删零件。",
    )


def _blocked_text(
    rows: list[_Scope],
    *,
    label: str,
    page: str,
    unaudited_note: str,
    rolling_back: bool,
    done: str,
) -> str:
    unaudited, approved = _split(rows)
    lead = "回滚不了：" if rolling_back else "删不了："
    tail = f"处理完再回到「{_CHANGE_PAGE}」重新删除这一本。" if rolling_back else done
    chunks: list[str] = []
    if unaudited:
        scopes = _join_scopes(unaudited)
        chunks.append(
            f"{lead}这些零件在以下范围还有未审核的{label}（{unaudited_note}）：{scopes}。"
        )
    if approved:
        scopes = _join_scopes(approved)
        chunks.append(
            f"{lead}这些零件在以下范围还有已审核的{label}：{scopes}。"
            f"已审核要先批量反审核，再批量删除。{_REVERSE}"
        )
    if not chunks:
        return ""
    return "".join(chunks) + f"请打开「{page}」。{_DELETE_FILTERS}{tail}"


def _split(rows: list[_Scope]) -> tuple[list[str], list[str]]:
    unaudited: list[str] = []
    approved: list[str] = []
    seen_open: set[str] = set()
    seen_approved: set[str] = set()
    for row in rows:
        label = row.label()
        if row.audit_status == AUDIT_APPROVED:
            if label not in seen_approved:
                seen_approved.add(label)
                approved.append(label)
        elif label not in seen_open:
            seen_open.add(label)
            unaudited.append(label)
    return unaudited, approved


def _join_scopes(labels: list[str]) -> str:
    return "；".join(labels)


def _cost_scopes(db: Session, part_ids: list[int]) -> list[_Scope]:
    sql = (
        "SELECT location, stamping_supplier, vehicle_model, version, year, month, audit_status "
        "FROM stamping_part_costs WHERE source_part_id IN :ids"
    )
    return [_scope(row) for row in _select_all(db, sql, part_ids)]


def _fee_scopes(db: Session, part_ids: list[int]) -> list[_Scope]:
    sql = (
        "SELECT location, stamping_supplier, vehicle_model, version, year, audit_status "
        "FROM stamping_process_fees WHERE source_part_id IN :ids"
    )
    return [_scope(row) for row in _select_all(db, sql, part_ids)]


def _scope(row: Row[tuple[Any, ...]]) -> _Scope:
    data = row._mapping
    month = data.get("month")
    return _Scope(
        location=str(data["location"]),
        supplier=str(data["stamping_supplier"]),
        vehicle_model=str(data["vehicle_model"]),
        version=str(data["version"]),
        year=int(data["year"]),
        month=int(month) if month is not None else None,
        audit_status=str(data["audit_status"]),
    )


def _select_all(db: Session, sql: str, part_ids: list[int]) -> list[Row[tuple[Any, ...]]]:
    found: list[Row[tuple[Any, ...]]] = []
    statement = text(sql).bindparams(bindparam("ids", expanding=True))
    for chunk in _chunks(part_ids):
        found.extend(db.execute(statement, {"ids": chunk}).all())
    return found


def _chunks(ids: list[int]) -> list[list[int]]:
    unique = list(dict.fromkeys(ids))
    return [unique[start : start + _CHUNK] for start in range(0, len(unique), _CHUNK)]
