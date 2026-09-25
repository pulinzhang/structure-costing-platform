"""按 logical_ref_filter 拼计数。过滤行就是表模型，不另做一份。"""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.models.settings.logical_ref.model import LogicalRefFilter

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_OPS = frozenset({"eq", "period_gte", "period_lte", "period_before_next"})
_NEXT_MODES = frozenset({"first", "after"})


def is_plain_identifier(name: str) -> bool:
    return _IDENTIFIER.fullmatch(name) is not None


def _quote(name: str) -> str:
    if not is_plain_identifier(name):
        raise ValueError(f"非法标识符: {name}")
    return f'"{name}"'


def count_sql(
    deleted_table: str,
    result_table: str,
    filters: Sequence[LogicalRefFilter],
    key_columns: tuple[str, ...],
    key_count: int,
) -> tuple[str, list[str]]:
    """返回 SQL 与按行展开的参数名。参数值由调用方绑定。"""
    _require_identifier(deleted_table)
    _require_identifier(result_table)
    for column in key_columns:
        _require_identifier(column)
    if key_count < 1:
        raise ValueError("没有被删行的键")
    if not filters:
        raise ValueError(f"{deleted_table} → {result_table} 没有过滤条件")
    aliases = _join_aliases(filters)
    joins = "".join(
        f" JOIN {_quote(table)} AS {alias}"
        f" ON src.{_quote(join_from)} = {alias}.{_quote(join_to)}"
        for (table, join_from, join_to), alias in aliases.items()
    )
    predicates = [_predicate(clause, aliases) for clause in filters]
    where = " AND ".join([_key_clause(key_columns, key_count), *predicates])
    sql = (
        f"SELECT COUNT(*) FROM {_quote(result_table)} AS hit "
        f"WHERE EXISTS ("
        f"SELECT 1 FROM {_quote(deleted_table)} AS src{joins} "
        f"WHERE {where}"
        f")"
    )
    names = [f"k{row}_{col}" for row in range(key_count) for col in range(len(key_columns))]
    return sql, names


def _join_aliases(filters: Sequence[LogicalRefFilter]) -> dict[tuple[str, str, str], str]:
    found: dict[tuple[str, str, str], str] = {}
    for clause in filters:
        if not clause.value_table:
            continue
        _require_identifier(clause.value_table)
        _require_identifier(clause.join_from_column or "")
        _require_identifier(clause.join_to_column or "")
        key = (clause.value_table, clause.join_from_column or "", clause.join_to_column or "")
        if key not in found:
            found[key] = f"via{len(found)}"
    return found


def _predicate(clause: LogicalRefFilter, aliases: dict[tuple[str, str, str], str]) -> str:
    if clause.compare not in _OPS:
        raise ValueError(f"比较算子无法解析: {clause.compare}")
    if clause.compare == "eq":
        return _eq(clause, aliases)
    if clause.compare == "period_before_next":
        return _before_next(clause)
    return _period(clause, aliases, closed=clause.compare == "period_lte")


def _eq(clause: LogicalRefFilter, aliases: dict[tuple[str, str, str], str]) -> str:
    _require_identifier(clause.result_column or "")
    _require_identifier(clause.value_column or "")
    return (
        f"hit.{_quote(clause.result_column or '')} = "
        f"{_value_alias(clause, aliases)}.{_quote(clause.value_column or '')}"
    )


def _period(
    clause: LogicalRefFilter,
    aliases: dict[tuple[str, str, str], str],
    *,
    closed: bool,
) -> str:
    _require_identifier(clause.result_year_column or "")
    _require_identifier(clause.result_month_column or "")
    _require_identifier(clause.value_column or "")
    _require_identifier(clause.value_month_column or "")
    result_year = f"hit.{_quote(clause.result_year_column or '')}"
    result_month = f"hit.{_quote(clause.result_month_column or '')}"
    alias = _value_alias(clause, aliases)
    value_year = f"{alias}.{_quote(clause.value_column or '')}"
    value_month = f"{alias}.{_quote(clause.value_month_column or '')}"
    if closed:
        return _not_ended(result_year, result_month, value_year, value_month)
    return _started(result_year, result_month, value_year, value_month)


def _before_next(clause: LogicalRefFilter) -> str:
    if clause.next_mode not in _NEXT_MODES:
        raise ValueError(f"下一行方式无法解析: {clause.next_mode}")
    for name in (
        clause.result_year_column,
        clause.result_month_column,
        clause.next_table,
        clause.next_group_column,
        clause.next_group_remote,
        clause.next_year_column,
        clause.next_month_column,
    ):
        _require_identifier(name or "")
    result_year = f"hit.{_quote(clause.result_year_column or '')}"
    result_month = f"hit.{_quote(clause.result_month_column or '')}"
    year_col = _quote(clause.next_year_column or "")
    month_col = _quote(clause.next_month_column or "")
    later = ""
    if clause.next_mode == "after":
        _require_identifier(clause.value_column or "")
        _require_identifier(clause.value_month_column or "")
        later = (
            " AND ("
            f"nxt.{year_col} > src.{_quote(clause.value_column or '')}"
            f" OR (nxt.{year_col} = src.{_quote(clause.value_column or '')}"
            f" AND nxt.{month_col} > src.{_quote(clause.value_month_column or '')})"
            ")"
        )
    rest = (
        f"FROM {_quote(clause.next_table or '')} AS nxt "
        f"WHERE nxt.{_quote(clause.next_group_remote or '')}"
        f" = src.{_quote(clause.next_group_column or '')}{later} "
        f"ORDER BY nxt.{year_col}, nxt.{month_col} LIMIT 1"
    )
    year_subquery = f"(SELECT nxt.{year_col} {rest})"
    month_subquery = f"(SELECT nxt.{month_col} {rest})"
    flags = _skip_flags(clause.skip_when)
    if flags:
        flag_sql = " OR ".join(f"src.{_quote(flag)} = 1" for flag in flags)
        year_expr = f"CASE WHEN {flag_sql} THEN NULL ELSE {year_subquery} END"
        month_expr = f"CASE WHEN {flag_sql} THEN NULL ELSE {month_subquery} END"
    else:
        year_expr = year_subquery
        month_expr = month_subquery
    return (
        f"({year_expr} IS NULL OR {result_year} < {year_expr} OR "
        f"({result_year} = {year_expr} AND {result_month} < {month_expr}))"
    )


def _skip_flags(raw: str | None) -> tuple[str, ...]:
    return tuple(piece.strip() for piece in (raw or "").split(",") if piece.strip())


def _value_alias(clause: LogicalRefFilter, aliases: dict[tuple[str, str, str], str]) -> str:
    if not clause.value_table:
        return "src"
    key = (clause.value_table, clause.join_from_column or "", clause.join_to_column or "")
    alias = aliases.get(key)
    if alias is None:
        raise ValueError(f"取值表未连接: {clause.value_table}")
    return alias


def _key_clause(key_columns: tuple[str, ...], key_count: int) -> str:
    if len(key_columns) == 1 and key_count == 1:
        return f"src.{_quote(key_columns[0])} = :k0_0"
    if len(key_columns) == 1:
        names = ", ".join(f":k{row}_0" for row in range(key_count))
        return f"src.{_quote(key_columns[0])} IN ({names})"
    tuples: list[str] = []
    for row in range(key_count):
        placeholders = ", ".join(f":k{row}_{col}" for col in range(len(key_columns)))
        tuples.append(f"({placeholders})")
    columns = ", ".join(f"src.{_quote(column)}" for column in key_columns)
    return f"({columns}) IN (VALUES {', '.join(tuples)})"


def _started(result_year: str, result_month: str, value_year: str, value_month: str) -> str:
    return (
        f"({result_year} > {value_year} OR "
        f"({result_year} = {value_year} AND {result_month} >= {value_month}))"
    )


def _not_ended(result_year: str, result_month: str, value_year: str, value_month: str) -> str:
    return (
        f"({value_year} IS NULL OR {result_year} < {value_year} OR "
        f"({result_year} = {value_year} AND {result_month} <= {value_month}))"
    )


def _require_identifier(name: str) -> None:
    if not is_plain_identifier(name):
        raise ValueError(f"非法标识符: {name}")
