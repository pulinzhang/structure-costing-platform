"""表注释、引用话术，以及删除前的外键发现与计数。不 commit。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.settings.ref_hint import RefHint
from app.models.settings.schema_comment import SchemaComment

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CHUNK = 400
_BLOCKING = frozenset({"RESTRICT", "NO ACTION"})


@dataclass(frozen=True)
class ForeignKeyRef:
    """指向父表的一组外键列。constraint_id 只在 child_table 内编号。"""

    child_table: str
    constraint_id: int
    parent_table: str
    parent_columns: tuple[str, ...]
    child_columns: tuple[str, ...]
    on_delete: str


def is_plain_identifier(name: str) -> bool:
    return _IDENTIFIER.fullmatch(name) is not None


def _quote(name: str) -> str:
    if not is_plain_identifier(name):
        raise ValueError(f"非法标识符: {name}")
    return f'"{name}"'


class SchemaCommentRepository:
    def list_table_names(self, db: Session) -> set[str]:
        rows = db.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ).all()
        return {str(row[0]) for row in rows if is_plain_identifier(str(row[0]))}

    def list_foreign_keys(self, db: Session) -> list[ForeignKeyRef]:
        found: list[ForeignKeyRef] = []
        for child_table in sorted(self.list_table_names(db)):
            rows = db.execute(text(f"PRAGMA foreign_key_list({_quote(child_table)})")).mappings()
            grouped: dict[int, list[dict[str, object]]] = {}
            for row in rows:
                grouped.setdefault(int(row["id"]), []).append(dict(row))
            for constraint_id, columns in grouped.items():
                ref = _ref_from_columns(child_table, constraint_id, columns)
                if ref is not None:
                    found.append(ref)
        return found

    def count_matches(
        self,
        db: Session,
        *,
        child_table: str,
        child_columns: tuple[str, ...],
        key_rows: list[tuple[object, ...]],
    ) -> int:
        if not key_rows:
            return 0
        total = 0
        for start in range(0, len(key_rows), _CHUNK):
            chunk = key_rows[start : start + _CHUNK]
            total += self._count_chunk(
                db,
                child_table=child_table,
                child_columns=child_columns,
                key_rows=chunk,
            )
        return total

    def load_names(self, db: Session, table_names: list[str]) -> dict[str, str]:
        if not table_names or "schema_comment" not in self.list_table_names(db):
            return {}
        params = {f"t{index}": name for index, name in enumerate(table_names)}
        placeholders = ", ".join(f":t{index}" for index in range(len(table_names)))
        rows = db.execute(
            text(
                "SELECT table_name, name_zh FROM schema_comment "
                f"WHERE table_name IN ({placeholders})"
            ),
            params,
        ).all()
        return {str(row[0]): str(row[1]) for row in rows if row[1]}

    def load_hints(self, db: Session, parent_table: str) -> dict[str, str]:
        if "ref_hint" not in self.list_table_names(db):
            return {}
        rows = db.execute(
            text("SELECT child_table, hint FROM ref_hint WHERE parent_table = :parent"),
            {"parent": parent_table},
        ).all()
        return {str(row[0]): str(row[1]) for row in rows if row[1]}

    def upsert_comment(
        self,
        db: Session,
        *,
        table_name: str,
        slice_name: str,
        name_zh: str,
        name_en: str,
    ) -> None:
        row = db.get(SchemaComment, table_name)
        if row is None:
            db.add(
                SchemaComment(
                    table_name=table_name,
                    slice=slice_name,
                    name_zh=name_zh,
                    name_en=name_en,
                )
            )
            return
        row.slice = slice_name
        row.name_zh = name_zh
        row.name_en = name_en

    def upsert_hint(
        self,
        db: Session,
        *,
        parent_table: str,
        child_table: str,
        hint: str,
    ) -> None:
        row = db.get(RefHint, (parent_table, child_table))
        if row is None:
            db.add(RefHint(parent_table=parent_table, child_table=child_table, hint=hint))
            return
        row.hint = hint

    def _count_chunk(
        self,
        db: Session,
        *,
        child_table: str,
        child_columns: tuple[str, ...],
        key_rows: list[tuple[object, ...]],
    ) -> int:
        quoted_table = _quote(child_table)
        quoted_columns = [_quote(column) for column in child_columns]
        params: dict[str, object] = {}
        if len(child_columns) == 1 and len(key_rows) == 1:
            sql = f"SELECT COUNT(*) FROM {quoted_table} WHERE {quoted_columns[0]} = :v0"
            params["v0"] = key_rows[0][0]
        elif len(child_columns) == 1:
            names = []
            for index, row in enumerate(key_rows):
                name = f"v{index}"
                names.append(f":{name}")
                params[name] = row[0]
            sql = (
                f"SELECT COUNT(*) FROM {quoted_table} "
                f"WHERE {quoted_columns[0]} IN ({', '.join(names)})"
            )
        elif len(key_rows) == 1:
            clauses = []
            for index, column in enumerate(quoted_columns):
                name = f"v{index}"
                clauses.append(f"{column} = :{name}")
                params[name] = key_rows[0][index]
            sql = f"SELECT COUNT(*) FROM {quoted_table} WHERE {' AND '.join(clauses)}"
        else:
            tuples: list[str] = []
            for row_index, row in enumerate(key_rows):
                placeholders: list[str] = []
                for column_index, value in enumerate(row):
                    name = f"v{row_index}_{column_index}"
                    placeholders.append(f":{name}")
                    params[name] = value
                tuples.append(f"({', '.join(placeholders)})")
            column_list = ", ".join(quoted_columns)
            sql = (
                f"SELECT COUNT(*) FROM {quoted_table} "
                f"WHERE ({column_list}) IN (VALUES {', '.join(tuples)})"
            )
        count = db.execute(text(sql), params).scalar_one()
        return int(count)


def _foreign_key_seq(column: dict[str, object]) -> int:
    seq = column["seq"]
    if isinstance(seq, int) and not isinstance(seq, bool):
        return seq
    if isinstance(seq, str):
        return int(seq)
    raise ValueError("外键列序号不是整数")


def _ref_from_columns(
    child_table: str,
    constraint_id: int,
    columns: list[dict[str, object]],
) -> ForeignKeyRef | None:
    columns.sort(key=_foreign_key_seq)
    parent_table = str(columns[0]["table"])
    parent_columns = tuple(str(item["to"]) for item in columns if item["to"])
    child_columns = tuple(str(item["from"]) for item in columns if item["from"])
    if len(parent_columns) != len(columns) or len(child_columns) != len(columns):
        return None
    names = (parent_table, *parent_columns, *child_columns)
    if not all(is_plain_identifier(name) for name in names):
        return None
    on_delete = str(columns[0]["on_delete"] or "NO ACTION").upper()
    return ForeignKeyRef(
        child_table=child_table,
        constraint_id=constraint_id,
        parent_table=parent_table,
        parent_columns=parent_columns,
        child_columns=child_columns,
        on_delete=on_delete,
    )


def is_blocking(on_delete: str) -> bool:
    return on_delete in _BLOCKING
