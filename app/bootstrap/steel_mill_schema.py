"""存量库给三张事实表补钢厂 id，并按种子回填。create_all 不改已有表。"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, OperationalError

from app.services.masterdata.steel_mill.normalize import mill_lookup_key
from app.services.masterdata.steel_mill.seed import STEEL_MILL_SEEDS
from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.steel_mill_schema")

_BASE = "steel_base_prices"
_POLICY = "steel_price_policies"
_RESULT = "steel_prices"
_SAMPLE_LIMIT = 20


def _foreign_keys_off(connection: Connection) -> None:
    """重建表时关掉外键。必须在事务开始前，走驱动连接，否则 SQLite 忽略这条 PRAGMA。"""
    driver = connection.connection.driver_connection
    if driver is None:
        raise RuntimeError("无法取得 SQLite 驱动连接，启动中止")
    cursor = driver.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.close()


def ensure_steel_mill_fact_schema(engine: Engine) -> None:
    """种子之后调用。空 id 或回填后业务键相撞则启动失败。"""
    try:
        with engine.connect() as connection:
            _foreign_keys_off(connection)
            with connection.begin():
                if not _table_exists(connection, "steel_mills"):
                    return
                _align_base_prices(connection)
                _align_policies(connection)
                _align_results(connection)
                _fold_into_anben(connection, _ANGANG_GROUP)
                _fold_into_anben(connection, "TAGAL")
                _repair_ladder_policy_fk(connection)
        logger.info("钢厂事实表结构已对齐")
    except OperationalError:
        logger.exception("无法补齐钢厂事实表")
        raise


_ANBEN = "鞍本"
_ANGANG_GROUP = "鞍钢集团"


def _fold_into_anben(connection: Connection, source_name: str) -> None:
    """这家写法就是鞍本。档案不单列，加减价字改成鞍本。"""
    anben_id = _mill_id_by_abbreviation(connection, _ANBEN)
    source_id = _mill_id_by_abbreviation(connection, source_name)
    if anben_id is None:
        if source_id is not None:
            raise RuntimeError(f"现网有「{source_name}」档案，但没有鞍本，无法收成一家，启动中止")
        return
    if source_id is not None:
        _assert_fold_unique(connection, source_id, anben_id, source_name)
        if _table_exists(connection, _POLICY):
            connection.execute(
                text(
                    f"UPDATE {_POLICY} SET steel_mill_id = :anben_id, steel_mill = :anben "
                    "WHERE steel_mill_id = :source_id"
                ),
                {"anben_id": anben_id, "anben": _ANBEN, "source_id": source_id},
            )
        if _table_exists(connection, _BASE):
            connection.execute(
                text(
                    f"UPDATE {_BASE} SET steel_mill_id = :anben_id, "
                    "canonical_steel_mill = :anben WHERE steel_mill_id = :source_id"
                ),
                {"anben_id": anben_id, "anben": _ANBEN, "source_id": source_id},
            )
        if _table_exists(connection, _RESULT):
            connection.execute(
                text(
                    f"UPDATE {_RESULT} SET steel_mill_id = :anben_id, "
                    "steel_mill = CASE WHEN steel_mill = :source_name THEN :anben ELSE steel_mill END "
                    "WHERE steel_mill_id = :source_id"
                ),
                {
                    "anben_id": anben_id,
                    "anben": _ANBEN,
                    "source_name": source_name,
                    "source_id": source_id,
                },
            )
        connection.execute(
            text("DELETE FROM steel_mills WHERE id = :source_id"),
            {"source_id": source_id},
        )
        logger.info("已把 %s 收成鞍本", source_name)
    _ensure_alias(connection, anben_id, source_name)


def _mill_id_by_abbreviation(connection: Connection, abbreviation: str) -> int | None:
    row = connection.execute(
        text("SELECT id FROM steel_mills WHERE abbreviation = :name"),
        {"name": abbreviation},
    ).first()
    if row is None:
        return None
    return int(row[0])


def _ensure_alias(connection: Connection, steel_mill_id: int, alias: str) -> None:
    row = connection.execute(
        text("SELECT steel_mill_id FROM steel_mill_aliases WHERE alias = :alias"),
        {"alias": alias},
    ).first()
    if row is None:
        connection.execute(
            text(
                "INSERT INTO steel_mill_aliases (alias, steel_mill_id) "
                "VALUES (:alias, :steel_mill_id)"
            ),
            {"alias": alias, "steel_mill_id": steel_mill_id},
        )
        return
    if int(row[0]) != steel_mill_id:
        raise RuntimeError(f"别名「{alias}」已属于另一家钢厂，启动中止")


def _assert_fold_unique(
    connection: Connection,
    source_id: int,
    anben_id: int,
    source_name: str,
) -> None:
    checks = (
        (
            _POLICY,
            "year, month, category_name, policy_type, grade_value, base_thickness",
            (
                "a.year = g.year AND a.month = g.month AND a.category_name = g.category_name "
                "AND a.policy_type = g.policy_type AND a.grade_value IS g.grade_value "
                "AND a.base_thickness IS g.base_thickness"
            ),
        ),
        (
            _BASE,
            "year, month, location, category_name, grade, thick, width",
            (
                "a.year = g.year AND a.month = g.month AND a.location = g.location "
                "AND a.category_name = g.category_name AND a.grade = g.grade "
                "AND a.thick IS g.thick AND a.width IS g.width"
            ),
        ),
        (
            _RESULT,
            "year, month, location, category_name, grade, thickness, width",
            (
                "a.year = g.year AND a.month = g.month AND a.location = g.location "
                "AND a.category_name = g.category_name AND a.grade = g.grade "
                "AND a.thickness IS g.thickness AND a.width IS g.width"
            ),
        ),
    )
    for table_name, columns, join_sql in checks:
        if not _table_exists(connection, table_name):
            continue
        if "steel_mill_id" not in _column_names(connection, table_name):
            continue
        selected = ", ".join(f"g.{name.strip()}" for name in columns.split(","))
        rows = connection.execute(
            text(
                f"SELECT {selected} FROM {table_name} g "
                f"JOIN {table_name} a ON {join_sql} "
                "WHERE g.steel_mill_id = :source_id AND a.steel_mill_id = :anben_id "
                "LIMIT :limit"
            ),
            {"source_id": source_id, "anben_id": anben_id, "limit": _SAMPLE_LIMIT},
        ).all()
        if rows:
            sample = "；".join(str(tuple(row)) for row in rows)
            raise RuntimeError(
                f"「{source_name}」收成鞍本后 {table_name} 业务键相撞，启动中止：{sample}"
            )


def _repair_ladder_policy_fk(connection: Connection) -> None:
    """重建政策表时，阶梯外键会跟着临时表名走。指回正式表，并重建联动结果上的外键。"""
    if not _table_exists(connection, "steel_price_ladder_items"):
        return
    parents = {
        str(row[2])
        for row in connection.execute(
            text("PRAGMA foreign_key_list(steel_price_ladder_items)")
        ).all()
    }
    if parents == {"steel_price_policies"}:
        return
    _rebuild(
        connection,
        "steel_price_ladder_items",
        "app.models.yishiyiyi.steel_price_policy",
        "SteelPriceLadderItem",
    )
    if _table_exists(connection, _RESULT):
        _rebuild(connection, _RESULT, "app.models.costing.steel_price", "SteelPrice")
    logger.info("已把阶梯明细外键指回 steel_price_policies")


def _align_base_prices(connection: Connection) -> None:
    if not _table_exists(connection, _BASE):
        return
    if _already_on_mill_id(connection, _BASE, "uix_base_price_business_key"):
        return
    _add_column(connection, _BASE, "canonical_steel_mill", "VARCHAR(50)")
    _add_column(connection, _BASE, "steel_mill_id", "INTEGER")
    _backfill_base_prices(connection)
    _assert_no_null_mill(connection, _BASE)
    _assert_unique(
        connection,
        _BASE,
        (
            "year",
            "month",
            "location",
            "steel_mill_id",
            "category_name",
            "grade",
            "thick",
            "width",
        ),
    )
    _rebuild(connection, _BASE, "app.models.yishiyiyi.steel_base_price", "SteelBasePrice")


def _align_policies(connection: Connection) -> None:
    if not _table_exists(connection, _POLICY):
        return
    if _already_on_mill_id(connection, _POLICY, "uix_policy_business_key"):
        return
    _add_column(connection, _POLICY, "steel_mill_id", "INTEGER")
    _backfill_policies(connection)
    _assert_no_null_mill(connection, _POLICY)
    _assert_unique(
        connection,
        _POLICY,
        (
            "year",
            "month",
            "steel_mill_id",
            "category_name",
            "policy_type",
            "grade_value",
            "base_thickness",
        ),
    )
    _rebuild(connection, _POLICY, "app.models.yishiyiyi.steel_price_policy", "SteelPricePolicy")


def _align_results(connection: Connection) -> None:
    if not _table_exists(connection, _RESULT):
        return
    if _already_on_mill_id(connection, _RESULT, "uix_steel_price_business_key"):
        return
    _add_column(connection, _RESULT, "steel_mill_id", "INTEGER")
    _backfill_results(connection)
    _assert_no_null_mill(connection, _RESULT)
    _assert_unique(
        connection,
        _RESULT,
        (
            "year",
            "month",
            "location",
            "steel_mill_id",
            "category_name",
            "grade",
            "thickness",
            "width",
        ),
    )
    _rebuild(connection, _RESULT, "app.models.costing.steel_price", "SteelPrice")


def _already_on_mill_id(connection: Connection, table_name: str, index_name: str) -> bool:
    if "steel_mill_id" not in _column_names(connection, table_name):
        return False
    if not _column_not_null(connection, table_name, "steel_mill_id"):
        return False
    sql = _index_sql(connection, index_name)
    return sql is not None and "steel_mill_id" in sql


def _backfill_base_prices(connection: Connection) -> None:
    full_by_key, id_by_full = _seed_lookup(connection)
    rows = connection.execute(
        text(
            f"SELECT id, steel_mill FROM {_BASE} "
            "WHERE steel_mill_id IS NULL OR canonical_steel_mill IS NULL"
        )
    ).all()
    for row_id, raw in rows:
        resolved = _resolve(full_by_key, id_by_full, raw)
        if resolved is None:
            continue
        mill_id, full_name = resolved
        connection.execute(
            text(
                f"UPDATE {_BASE} SET steel_mill_id = :mill_id, "
                "canonical_steel_mill = :full_name WHERE id = :row_id"
            ),
            {"mill_id": mill_id, "full_name": full_name, "row_id": row_id},
        )


def _backfill_policies(connection: Connection) -> None:
    full_by_key, id_by_full = _seed_lookup(connection)
    rows = connection.execute(
        text(f"SELECT id, steel_mill FROM {_POLICY} WHERE steel_mill_id IS NULL")
    ).all()
    for row_id, raw in rows:
        resolved = _resolve(full_by_key, id_by_full, raw)
        if resolved is None:
            continue
        mill_id, full_name = resolved
        connection.execute(
            text(
                f"UPDATE {_POLICY} SET steel_mill_id = :mill_id, steel_mill = :full_name "
                "WHERE id = :row_id"
            ),
            {"mill_id": mill_id, "full_name": full_name, "row_id": row_id},
        )


def _backfill_results(connection: Connection) -> None:
    full_by_key, id_by_full = _seed_lookup(connection)
    rows = connection.execute(
        text(f"SELECT id, steel_mill FROM {_RESULT} WHERE steel_mill_id IS NULL")
    ).all()
    for row_id, raw in rows:
        resolved = _resolve(full_by_key, id_by_full, raw)
        if resolved is None:
            continue
        mill_id, _full_name = resolved
        connection.execute(
            text(f"UPDATE {_RESULT} SET steel_mill_id = :mill_id WHERE id = :row_id"),
            {"mill_id": mill_id, "row_id": row_id},
        )


def _seed_lookup(connection: Connection) -> tuple[dict[str, str], dict[str, int]]:
    full_by_key: dict[str, str] = {}
    for seed in STEEL_MILL_SEEDS:
        for raw in (seed.abbreviation, seed.full_name, *seed.aliases):
            full_by_key[mill_lookup_key(raw)] = seed.full_name
    id_by_full: dict[str, int] = {}
    stored = connection.execute(text("SELECT id, full_name FROM steel_mills")).all()
    for mill_id, full_name in stored:
        id_by_full[mill_lookup_key(str(full_name))] = int(mill_id)
    return full_by_key, id_by_full


def _resolve(
    full_by_key: dict[str, str],
    id_by_full: dict[str, int],
    raw: object,
) -> tuple[int, str] | None:
    full_name = full_by_key.get(mill_lookup_key(None if raw is None else str(raw)))
    if full_name is None:
        return None
    mill_id = id_by_full.get(mill_lookup_key(full_name))
    if mill_id is None:
        return None
    return mill_id, full_name


def _assert_no_null_mill(connection: Connection, table_name: str) -> None:
    rows = connection.execute(
        text(
            f"SELECT year, month, steel_mill FROM {table_name} "
            "WHERE steel_mill_id IS NULL LIMIT :limit"
        ),
        {"limit": _SAMPLE_LIMIT},
    ).all()
    if not rows:
        return
    sample = "；".join(f"{table_name} {year}年{month}月「{raw}」" for year, month, raw in rows)
    raise RuntimeError(f"钢厂回填后仍有空 id，启动中止：{sample}")


def _assert_unique(connection: Connection, table_name: str, columns: tuple[str, ...]) -> None:
    col_sql = ", ".join(columns)
    rows = connection.execute(text(f"SELECT {col_sql} FROM {table_name}")).all()
    seen: dict[tuple[object, ...], int] = {}
    for row in rows:
        key = tuple(row)
        if any(value is None for value in key):
            continue
        seen[key] = seen.get(key, 0) + 1
    collisions = [key for key, count in seen.items() if count > 1]
    if not collisions:
        return
    sample = "；".join(str(key) for key in collisions[:_SAMPLE_LIMIT])
    raise RuntimeError(f"{table_name} 按钢厂 id 后业务键相撞，启动中止：{sample}")


def _rebuild(connection: Connection, table_name: str, module_name: str, class_name: str) -> None:
    import importlib

    model = getattr(importlib.import_module(module_name), class_name)
    old_name = f"{table_name}__mig"
    for index_name in _named_indexes(connection, table_name):
        connection.execute(text(f'DROP INDEX "{index_name}"'))
    connection.execute(text(f'ALTER TABLE "{table_name}" RENAME TO "{old_name}"'))
    model.__table__.create(connection)
    shared = [
        name
        for name in _column_names_ordered(connection, table_name)
        if name in _column_names(connection, old_name)
    ]
    column_sql = ", ".join(f'"{name}"' for name in shared)
    try:
        connection.execute(
            text(f'INSERT INTO "{table_name}" ({column_sql}) SELECT {column_sql} FROM "{old_name}"')
        )
    except IntegrityError as exc:
        raise RuntimeError(f"{table_name} 重建时业务键或外键失败，启动中止") from exc
    connection.execute(text(f'DROP TABLE "{old_name}"'))
    logger.info("已重建 %s，唯一键改为 steel_mill_id", table_name)


def _add_column(connection: Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name in _column_names(connection, table_name):
        return
    connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}'))
    logger.info("已加列 %s.%s", table_name, column_name)


def _table_exists(connection: Connection, table_name: str) -> bool:
    row = connection.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": table_name},
    ).first()
    return row is not None


def _column_names(connection: Connection, table_name: str) -> set[str]:
    return set(_column_names_ordered(connection, table_name))


def _column_names_ordered(connection: Connection, table_name: str) -> list[str]:
    rows = connection.execute(text(f'PRAGMA table_info("{table_name}")')).all()
    return [str(row[1]) for row in rows]


def _column_not_null(connection: Connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute(text(f'PRAGMA table_info("{table_name}")')).all()
    for row in rows:
        if str(row[1]) == column_name:
            return int(row[3]) == 1
    return False


def _index_sql(connection: Connection, index_name: str) -> str | None:
    row = connection.execute(
        text("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = :name"),
        {"name": index_name},
    ).first()
    if row is None or row[0] is None:
        table_row = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE type = 'table' " "AND sql LIKE :pattern"),
            {"pattern": f"%{index_name}%"},
        ).first()
        if table_row is None or table_row[0] is None:
            return None
        return str(table_row[0])
    return str(row[0])


def _named_indexes(connection: Connection, table_name: str) -> list[str]:
    rows = connection.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = :name "
            "AND sql IS NOT NULL"
        ),
        {"name": table_name},
    ).all()
    return [str(row[0]) for row in rows]
