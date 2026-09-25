"""逻辑引用的读写。不发现外键，不调用外键仓库。"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.settings.logical_ref.model import LogicalRef, LogicalRefFilter
from app.repositories.settings.logical_ref.sql import count_sql, is_plain_identifier


class LogicalRefRepository:
    def list_table_names(self, db: Session) -> set[str]:
        rows = db.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ).all()
        return {str(row[0]) for row in rows if is_plain_identifier(str(row[0]))}

    def list_heads(self, db: Session, deleted_table: str) -> list[LogicalRef]:
        if "logical_ref" not in self.list_table_names(db):
            return []
        if "logical_ref_filter" not in self.list_table_names(db):
            return []
        return list(
            db.scalars(
                select(LogicalRef)
                .where(LogicalRef.deleted_table == deleted_table)
                .order_by(LogicalRef.result_table)
            ).all()
        )

    def count(
        self,
        db: Session,
        head: LogicalRef,
        key_columns: tuple[str, ...],
        key_rows: list[tuple[object, ...]],
    ) -> int:
        if not key_rows:
            return 0
        filters = db.scalars(
            select(LogicalRefFilter)
            .where(
                LogicalRefFilter.deleted_table == head.deleted_table,
                LogicalRefFilter.result_table == head.result_table,
            )
            .order_by(LogicalRefFilter.seq)
        ).all()
        sql, names = count_sql(
            head.deleted_table,
            head.result_table,
            filters,
            key_columns,
            len(key_rows),
        )
        params: dict[str, object] = {}
        for index, name in enumerate(names):
            row_index, column_index = divmod(index, len(key_columns))
            params[name] = key_rows[row_index][column_index]
        count = db.execute(text(sql), params).scalar_one()
        return int(count)

    def insert_if_absent(
        self, db: Session, row: LogicalRef, filters: list[LogicalRefFilter]
    ) -> None:
        """这一对表还没有头时才插入头和过滤。已有行、种子里没有的配置都留下。"""
        current = db.get(LogicalRef, (row.deleted_table, row.result_table))
        if current is not None:
            return
        db.add(row)
        for clause in filters:
            db.add(clause)
