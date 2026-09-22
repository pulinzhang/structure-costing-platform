"""存量库补列 / 改 UNIQUE / 回填生失效（create_all 不改已有表）。"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

from app.bootstrap.sqlite_rebuild import column_names, table_exists
from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.effective_period_schema")

_BOM_NODE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("location", "VARCHAR(50)"),
    ("vehicle_model", "VARCHAR(50)"),
    ("bom_version", "VARCHAR(20)"),
    ("effective_year", "INTEGER"),
    ("effective_month", "INTEGER"),
    ("expiry_year", "INTEGER"),
    ("expiry_month", "INTEGER"),
)
_STAMPING_PERIOD_COLUMNS: tuple[tuple[str, str], ...] = (
    ("effective_year", "INTEGER"),
    ("effective_month", "INTEGER"),
    ("expiry_year", "INTEGER"),
    ("expiry_month", "INTEGER"),
)


def ensure_effective_period_schema(engine: Engine) -> None:
    try:
        with engine.begin() as connection:
            if not table_exists(connection, "bom_nodes"):
                return
            _add_missing_columns(connection, "bom_nodes", _BOM_NODE_COLUMNS)
            _add_missing_columns(connection, "stamping_parts", _STAMPING_PERIOD_COLUMNS)
            _add_missing_columns(connection, "stamping_die_parts", _STAMPING_PERIOD_COLUMNS)
            _backfill_bom_nodes(connection)
            _backfill_stamping_period(connection, "stamping_parts")
            _backfill_stamping_period(connection, "stamping_die_parts")
            _assert_no_unique_conflicts(connection)
            _ensure_indexes(connection)
            _ensure_welding_fee_unique(connection)
            _ensure_assembly_cost_unique(connection)
        logger.info("生失效表结构已对齐")
    except OperationalError:
        logger.exception("无法补齐生失效表结构")
        raise


def _add_missing_columns(
    connection: Connection,
    table_name: str,
    columns: tuple[tuple[str, str], ...],
) -> None:
    existing = column_names(connection, table_name)
    for name, sql_type in columns:
        if name in existing:
            continue
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {sql_type}"))
        logger.info("已加列 %s.%s", table_name, name)


def _backfill_bom_nodes(connection: Connection) -> None:
    connection.execute(
        text(
            """
            UPDATE bom_nodes
            SET
                location = (
                    SELECT location FROM bom_snapshots WHERE bom_snapshots.id = bom_nodes.snapshot_id
                ),
                vehicle_model = (
                    SELECT vehicle_model FROM bom_snapshots
                    WHERE bom_snapshots.id = bom_nodes.snapshot_id
                ),
                bom_version = (
                    SELECT bom_version FROM bom_snapshots
                    WHERE bom_snapshots.id = bom_nodes.snapshot_id
                )
            WHERE location IS NULL OR location = ''
               OR vehicle_model IS NULL OR vehicle_model = ''
               OR bom_version IS NULL OR bom_version = ''
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE bom_nodes
            SET
                effective_year = (
                    SELECT effective_year FROM vehicle_models
                    WHERE vehicle_models.location = bom_nodes.location
                      AND vehicle_models.vehicle_model = bom_nodes.vehicle_model
                ),
                effective_month = (
                    SELECT effective_month FROM vehicle_models
                    WHERE vehicle_models.location = bom_nodes.location
                      AND vehicle_models.vehicle_model = bom_nodes.vehicle_model
                ),
                expiry_year = (
                    SELECT expiry_year FROM vehicle_models
                    WHERE vehicle_models.location = bom_nodes.location
                      AND vehicle_models.vehicle_model = bom_nodes.vehicle_model
                ),
                expiry_month = (
                    SELECT expiry_month FROM vehicle_models
                    WHERE vehicle_models.location = bom_nodes.location
                      AND vehicle_models.vehicle_model = bom_nodes.vehicle_model
                )
            WHERE effective_year IS NULL OR effective_month IS NULL
            """
        )
    )


def _backfill_stamping_period(connection: Connection, table_name: str) -> None:
    connection.execute(
        text(
            f"""
            UPDATE {table_name}
            SET
                effective_year = (
                    SELECT effective_year FROM vehicle_models
                    WHERE vehicle_models.location = {table_name}.location
                      AND vehicle_models.vehicle_model = {table_name}.vehicle_model
                ),
                effective_month = (
                    SELECT effective_month FROM vehicle_models
                    WHERE vehicle_models.location = {table_name}.location
                      AND vehicle_models.vehicle_model = {table_name}.vehicle_model
                ),
                expiry_year = (
                    SELECT expiry_year FROM vehicle_models
                    WHERE vehicle_models.location = {table_name}.location
                      AND vehicle_models.vehicle_model = {table_name}.vehicle_model
                ),
                expiry_month = (
                    SELECT expiry_month FROM vehicle_models
                    WHERE vehicle_models.location = {table_name}.location
                      AND vehicle_models.vehicle_model = {table_name}.vehicle_model
                )
            WHERE effective_year IS NULL OR effective_month IS NULL
            """
        )
    )


def _assert_no_unique_conflicts(connection: Connection) -> None:
    l0_dupes = connection.execute(
        text(
            """
            SELECT snapshot_id, part_number, COUNT(*) AS row_count
            FROM bom_nodes
            WHERE level = 0
            GROUP BY snapshot_id, part_number
            HAVING COUNT(*) > 1
            """
        )
    ).all()
    if l0_dupes:
        sample = ", ".join(
            f"snapshot={row.snapshot_id} {row.part_number}×{row.row_count}" for row in l0_dupes[:8]
        )
        raise RuntimeError(f"同一 snapshot 两个 L0 同零件号，禁止静默删：{sample}")

    part_dupes = connection.execute(
        text(
            """
            SELECT location, stamping_supplier, vehicle_model, part_number, COUNT(*) AS row_count
            FROM stamping_parts
            GROUP BY location, stamping_supplier, vehicle_model, part_number
            HAVING COUNT(*) > 1
            """
        )
    ).all()
    if part_dupes:
        sample = ", ".join(
            f"{row.location}/{row.stamping_supplier}/{row.vehicle_model}/{row.part_number}×{row.row_count}"
            for row in part_dupes[:8]
        )
        raise RuntimeError(f"冲压零件去掉 version 身份后同号多行，禁止静默删：{sample}")


def _ensure_indexes(connection: Connection) -> None:
    connection.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uix_bom_node_l0_part_number "
            "ON bom_nodes (snapshot_id, part_number) WHERE level = 0"
        )
    )
    index_sql = connection.execute(
        text("SELECT sql FROM sqlite_master WHERE type='index' AND name='uix_part_unique_key'")
    ).scalar()
    if index_sql and "version" in index_sql.lower():
        connection.execute(text("DROP INDEX uix_part_unique_key"))
        index_sql = None
    if not index_sql:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX uix_part_unique_key ON stamping_parts "
                "(location, stamping_supplier, vehicle_model, part_number)"
            )
        )


def _ensure_welding_fee_unique(connection: Connection) -> None:
    if not table_exists(connection, "bom_welding_fees"):
        return
    index_sql = connection.execute(
        text(
            "SELECT sql FROM sqlite_master "
            "WHERE type='index' AND name='uix_bom_welding_fee_scope_node'"
        )
    ).scalar()
    if index_sql and "bom_version" in index_sql.lower():
        connection.execute(text("DROP INDEX uix_bom_welding_fee_scope_node"))
        index_sql = None
    if not index_sql:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX uix_bom_welding_fee_scope_node "
                "ON bom_welding_fees (year, location, vehicle_model, source_breakdown_node_id)"
            )
        )


def _ensure_assembly_cost_unique(connection: Connection) -> None:
    if not table_exists(connection, "costing_assembly_costs"):
        return
    index_sql = connection.execute(
        text(
            "SELECT sql FROM sqlite_master "
            "WHERE type='index' AND name='uix_assembly_cost_scope_node'"
        )
    ).scalar()
    if index_sql and "bom_version" in index_sql.lower():
        connection.execute(text("DROP INDEX uix_assembly_cost_scope_node"))
        index_sql = None
    if not index_sql:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX uix_assembly_cost_scope_node "
                "ON costing_assembly_costs "
                "(year, month, location, vehicle_model, source_node_id)"
            )
        )
