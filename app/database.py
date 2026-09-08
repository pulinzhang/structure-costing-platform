"""
数据库配置模块
提供 SQLAlchemy 数据库连接和会话管理

主业务库（DatabaseConfig）与辅助库（AuxiliaryDatabaseConfig）隔离：
无 Redis 时，辅助库承载会话 Token、异步任务进度等短生命周期数据，
SQLite 使用独立文件，写入不受主业务长事务锁影响。
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.timezone import CHINA_TZ_NAME
from app.config import settings
from app.utils.logging_config import get_logger

logger = get_logger("database")


class Base(DeclarativeBase):
    """主业务库 ORM 基类。"""


class AuxiliaryBase(DeclarativeBase):
    """辅助库 ORM 基类（Token / 异步任务等）。"""


def _configure_sqlite_connection(dbapi_connection: object, connection_record: object) -> None:
    """SQLite：外键 + WAL；时间按东八区墙钟由应用层 now() 写入。"""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def _configure_postgres_connection(dbapi_connection: object, connection_record: object) -> None:
    """PostgreSQL：会话时区固定为东八区。"""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute(f"SET TIME ZONE '{CHINA_TZ_NAME}'")
    cursor.close()


def _create_engine_for_url(database_url: str, *, label: str) -> Engine:
    """按 URL 创建引擎（SQLite / PostgreSQL）。"""
    if "sqlite" in database_url:
        connect_args = {
            "check_same_thread": False,
            "timeout": 30,
        }
        if "mode=memory" in database_url or database_url.endswith(":memory:"):
            engine = create_engine(
                database_url,
                connect_args=connect_args,
                poolclass=StaticPool,
                echo=settings.IS_DEBUG,
            )
        else:
            engine = create_engine(
                database_url,
                connect_args=connect_args,
                echo=settings.IS_DEBUG,
            )
        event.listen(engine, "connect", _configure_sqlite_connection)
        logger.info(
            "%s SQLite 引擎创建成功: %s（业务时区 %s）",
            label,
            database_url,
            CHINA_TZ_NAME,
        )
        return engine

    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.IS_DEBUG,
    )
    event.listen(engine, "connect", _configure_postgres_connection)
    logger.info("%s PostgreSQL 引擎创建成功（TIME ZONE %s）", label, CHINA_TZ_NAME)
    return engine


class DatabaseConfig:
    """主业务数据库配置"""

    _engine: Engine | None = None
    _session_factory: sessionmaker[Session] | None = None

    @classmethod
    def get_engine(cls) -> Engine:
        if cls._engine is None:
            cls._engine = _create_engine_for_url(
                settings.DATABASE_URL,
                label="主业务库",
            )
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> sessionmaker[Session]:
        if cls._session_factory is None:
            engine = cls.get_engine()
            cls._session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return cls._session_factory

    @classmethod
    def create_tables(cls) -> None:
        engine = cls.get_engine()
        cls._migrate_welding_fee_tables(engine)
        cls._migrate_assembly_cost_tables(engine)
        Base.metadata.create_all(bind=engine)
        cls._ensure_sqlite_columns(engine)
        cls._ensure_welding_fee_columns(engine)
        cls._ensure_vehicle_model_child_fks(engine)
        cls._remap_welding_fee_permissions(engine)
        cls._remap_assembly_cost_permissions(engine)
        logger.info("主业务库表创建完成")

    @classmethod
    def _ensure_sqlite_columns(cls, engine: Engine) -> None:
        """为已有 SQLite 库补齐 create_all 不会添加的新列。"""
        if not str(engine.url).startswith("sqlite"):
            return
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        fee_table = "stamping_process_fees"
        if fee_table in table_names:
            fee_cols = {col["name"] for col in inspector.get_columns(fee_table)}
            if "is_tailor_welded" not in fee_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {fee_table} "
                            "ADD COLUMN is_tailor_welded BOOLEAN NOT NULL DEFAULT 0"
                        )
                    )
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS "
                            "ix_stamping_process_fee_is_tailor_welded "
                            f"ON {fee_table} (is_tailor_welded)"
                        )
                    )
                    conn.execute(
                        text(
                            f"UPDATE {fee_table} SET is_tailor_welded = 1 "
                            "WHERE source_part_id IS NOT NULL AND EXISTS ("
                            "SELECT 1 FROM stamping_parts p "
                            f"WHERE p.id = {fee_table}.source_part_id "
                            "AND p.is_tailor_welded = 1"
                            ")"
                        )
                    )
                    conn.execute(
                        text(
                            f"UPDATE {fee_table} SET is_tailor_welded = 1 "
                            "WHERE is_tailor_welded = 0 AND EXISTS ("
                            "SELECT 1 FROM stamping_parts p "
                            f"WHERE p.location = {fee_table}.location "
                            f"AND p.stamping_supplier = {fee_table}.stamping_supplier "
                            f"AND p.vehicle_model = {fee_table}.vehicle_model "
                            f"AND p.version = {fee_table}.version "
                            f"AND p.part_number = {fee_table}.part_number "
                            "AND p.is_tailor_welded = 1"
                            ")"
                        )
                    )
                logger.info("已为 %s 追加列 is_tailor_welded 并回填", fee_table)
            if "other_fee" not in fee_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {fee_table} " "ADD COLUMN other_fee NUMERIC(12, 3)")
                    )
                logger.info("已为 %s 追加列 other_fee", fee_table)
            if "manual_unit_price" in fee_cols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {fee_table} DROP COLUMN manual_unit_price"))
                logger.info("已从 %s 删除列 manual_unit_price", fee_table)

        config_table = "system_configs"
        if config_table in table_names:
            config_cols = {col["name"] for col in inspector.get_columns(config_table)}
            config_new_columns = (
                ("finished_finance_rate", "NUMERIC(8, 6) NOT NULL DEFAULT 0.02"),
                ("finished_management_rate", "NUMERIC(8, 6) NOT NULL DEFAULT 0.02"),
                (
                    "finished_warehouse_packaging_rate",
                    "NUMERIC(8, 6) NOT NULL DEFAULT 0.01",
                ),
                ("finished_scrap_rate", "NUMERIC(8, 6) NOT NULL DEFAULT 0.003"),
                (
                    "finished_pretax_profit_rate",
                    "NUMERIC(8, 6) NOT NULL DEFAULT 0.02",
                ),
                (
                    "swing_shear_process_fee_per_ton",
                    "NUMERIC(12, 4) NOT NULL DEFAULT 150",
                ),
            )
            for column_name, column_def in config_new_columns:
                if column_name in config_cols:
                    continue
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {config_table} " f"ADD COLUMN {column_name} {column_def}"
                        )
                    )
                logger.info("已为 %s 追加列 %s", config_table, column_name)

        part_table = "stamping_parts"
        if part_table in table_names:
            part_cols = {col["name"] for col in inspector.get_columns(part_table)}
            if "is_offal_nested" not in part_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {part_table} "
                            "ADD COLUMN is_offal_nested BOOLEAN NOT NULL DEFAULT 0"
                        )
                    )
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_part_is_offal_nested "
                            f"ON {part_table} (is_offal_nested)"
                        )
                    )
                    if "offal_source" not in part_cols:
                        conn.execute(
                            text(f"ALTER TABLE {part_table} ADD COLUMN offal_source VARCHAR(50)")
                        )
                    cls._backfill_offal_from_sheet_type(conn, part_table)
                logger.info(
                    "已为 %s 追加列 is_offal_nested / offal_source 并按料片式样回填", part_table
                )
            elif "offal_source" not in part_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {part_table} ADD COLUMN offal_source VARCHAR(50)")
                    )
                logger.info("已为 %s 追加列 offal_source", part_table)
            part_cols = {col["name"] for col in inspector.get_columns(part_table)}
            if "is_scrap_byproduct" not in part_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {part_table} "
                            "ADD COLUMN is_scrap_byproduct BOOLEAN NOT NULL DEFAULT 0"
                        )
                    )
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_part_is_scrap_byproduct "
                            f"ON {part_table} (is_scrap_byproduct)"
                        )
                    )
                logger.info("已为 %s 追加列 is_scrap_byproduct", part_table)
            part_cols = {col["name"] for col in inspector.get_columns(part_table)}
            if "has_swing_shear" not in part_cols:
                from app.common.swing_shear import SWING_SHEAR_MARK

                swing_like = f"%{SWING_SHEAR_MARK}%"
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {part_table} "
                            "ADD COLUMN has_swing_shear BOOLEAN NOT NULL DEFAULT 0"
                        )
                    )
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_part_has_swing_shear "
                            f"ON {part_table} (has_swing_shear)"
                        )
                    )
                    if "stamping_processes" in table_names:
                        conn.execute(
                            text(
                                f"UPDATE {part_table} SET has_swing_shear = 1 "
                                "WHERE EXISTS ("
                                "SELECT 1 FROM stamping_processes p "
                                f"WHERE p.part_id = {part_table}.id "
                                "AND (IFNULL(p.process_code, '') LIKE :swing_like "
                                "OR IFNULL(p.process_seq, '') LIKE :swing_like)"
                                ")"
                            ),
                            {"swing_like": swing_like},
                        )
                logger.info("已为 %s 追加列 has_swing_shear 并按工序回填", part_table)

        cost_table = "stamping_part_costs"
        if cost_table in table_names:
            cost_cols = {col["name"] for col in inspector.get_columns(cost_table)}
            cost_new_columns = (
                ("direct_cost", "NUMERIC(14, 6)"),
                ("finished_finance_fee", "NUMERIC(14, 6)"),
                ("finished_management_fee", "NUMERIC(14, 6)"),
                ("finished_warehouse_packaging_fee", "NUMERIC(14, 6)"),
                ("finished_pretax_profit_fee", "NUMERIC(14, 6)"),
                ("die_fee_id", "INTEGER"),
                ("die_fee_amount", "NUMERIC(14, 6)"),
                ("gauge_fee_id", "INTEGER"),
                ("gauge_fee_amount", "NUMERIC(14, 6)"),
                ("is_offal_nested", "BOOLEAN NOT NULL DEFAULT 0"),
                ("offal_source", "VARCHAR(50)"),
                ("has_swing_shear", "BOOLEAN NOT NULL DEFAULT 0"),
                ("swing_shear_fee_per_ton", "NUMERIC(12, 4) NOT NULL DEFAULT 0"),
            )
            for column_name, column_def in cost_new_columns:
                if column_name in cost_cols:
                    continue
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {cost_table} " f"ADD COLUMN {column_name} {column_def}")
                    )
                logger.info("已为 %s 追加列 %s", cost_table, column_name)
            if "has_swing_shear" not in cost_cols and "stamping_parts" in table_names:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"UPDATE {cost_table} SET has_swing_shear = 1 "
                            "WHERE has_swing_shear = 0 AND EXISTS ("
                            "SELECT 1 FROM stamping_parts p "
                            f"WHERE p.id = {cost_table}.source_part_id "
                            "AND p.has_swing_shear = 1"
                            ")"
                        )
                    )
                logger.info("已按零件主表回填 %s.has_swing_shear", cost_table)

        pkg_table = "bom_packaging_transport_fees"
        if pkg_table in table_names:
            pkg_cols = {col["name"] for col in inspector.get_columns(pkg_table)}
            pkg_new_columns = (
                ("excel_filename", "VARCHAR(255)"),
                ("sheet_name", "VARCHAR(100)"),
                ("excel_row", "INTEGER"),
            )
            for column_name, column_def in pkg_new_columns:
                if column_name in pkg_cols:
                    continue
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {pkg_table} " f"ADD COLUMN {column_name} {column_def}")
                    )
                logger.info("已为 %s 追加列 %s", pkg_table, column_name)

        llm_report_table = "llm_analysis_reports"
        if llm_report_table in table_names:
            llm_cols = {col["name"] for col in inspector.get_columns(llm_report_table)}
            llm_new_columns = (
                ("trace_id", "VARCHAR(36)"),
                ("prompt_preview", "TEXT"),
                ("llm_response_preview", "TEXT"),
            )
            for column_name, column_def in llm_new_columns:
                if column_name in llm_cols:
                    continue
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {llm_report_table} "
                            f"ADD COLUMN {column_name} {column_def}"
                        )
                    )
                logger.info("已为 %s 追加列 %s", llm_report_table, column_name)

        obsolete_table = "llm_monthly_cost_summary"
        if obsolete_table in table_names:
            with engine.begin() as conn:
                conn.execute(text(f"DROP TABLE {obsolete_table}"))
            logger.info("已删除废弃表 %s", obsolete_table)

        process_table = "stamping_processes"
        if process_table in table_names:
            process_cols = {col["name"] for col in inspector.get_columns(process_table)}
            if "die_number" not in process_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {process_table} ADD COLUMN die_number VARCHAR(80)")
                    )
                logger.info("已为 %s 追加列 die_number", process_table)

        die_process_table = "stamping_die_processes"
        if die_process_table in table_names:
            die_process_cols = {col["name"] for col in inspector.get_columns(die_process_table)}
            if "die_number" not in die_process_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {die_process_table} ADD COLUMN die_number VARCHAR(80)")
                    )
                logger.info("已为 %s 追加列 die_number", die_process_table)

        die_table = "stamping_die_parts"
        if die_table in table_names:
            die_cols = {col["name"] for col in inspector.get_columns(die_table)}
            if "alloc_status" in die_cols:
                with engine.begin() as conn:
                    conn.execute(text("DROP INDEX IF EXISTS ix_die_part_alloc_status"))
                    conn.execute(text(f"ALTER TABLE {die_table} DROP COLUMN alloc_status"))
                logger.info("已从 %s 删除列 alloc_status", die_table)
            if "stamping_supplier" not in die_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {die_table} ADD COLUMN stamping_supplier VARCHAR(100)")
                    )
                logger.info("已为 %s 追加列 stamping_supplier", die_table)
            if "version" not in die_cols:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {die_table} ADD COLUMN version VARCHAR(20)"))
                logger.info("已为 %s 追加列 version", die_table)

        die_fee_table = "stamping_die_fees"
        if die_fee_table in table_names:
            die_fee_cols = {col["name"] for col in inspector.get_columns(die_fee_table)}
            if "stamping_supplier" not in die_fee_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {die_fee_table} ADD COLUMN stamping_supplier VARCHAR(100)"
                        )
                    )
                logger.info("已为 %s 追加列 stamping_supplier", die_fee_table)
            if "version" not in die_fee_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {die_fee_table} ADD COLUMN version VARCHAR(20)")
                    )
                logger.info("已为 %s 追加列 version", die_fee_table)

        calc_log_table = "stamping_die_fee_calc_logs"
        if calc_log_table in table_names:
            calc_log_cols = {col["name"] for col in inspector.get_columns(calc_log_table)}
            if "stamping_supplier" not in calc_log_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {calc_log_table} "
                            "ADD COLUMN stamping_supplier VARCHAR(100)"
                        )
                    )
                logger.info("已为 %s 追加列 stamping_supplier", calc_log_table)
            if "version" not in calc_log_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {calc_log_table} ADD COLUMN version VARCHAR(20)")
                    )
                logger.info("已为 %s 追加列 version", calc_log_table)

        steel_calc_log_table = "steel_price_calc_logs"
        if steel_calc_log_table in table_names:
            steel_calc_log_cols = {
                col["name"] for col in inspector.get_columns(steel_calc_log_table)
            }
            for unused_col in ("stamping_supplier", "vehicle_model"):
                if unused_col not in steel_calc_log_cols:
                    continue
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {steel_calc_log_table} DROP COLUMN {unused_col}")
                    )
                logger.info("已从 %s 删除列 %s", steel_calc_log_table, unused_col)

    @classmethod
    def _migrate_assembly_cost_tables(cls, engine: Engine) -> None:
        """开发期改过表名/唯一键：SQLite 改不了表内 UNIQUE，错了就删表，由 create_all 重建。

        不搬旧行。T13J 等是测试数据，丢了重算即可。
        """
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assembly_tables = {
            "costing_assembly_costs",
            "costing_assembly_cost_items",
            "costing_assembly_cost_indirects",
            "costing_assembly_cost_calc_logs",
            "costing_l0_assembly_costs",
            "costing_l0_assembly_cost_items",
            "costing_l0_assembly_cost_indirects",
            "costing_l0_assembly_cost_calc_logs",
        }
        if not (tables & assembly_tables):
            return
        with engine.begin() as conn:
            if conn.dialect.name != "sqlite":
                return
            present = {
                str(name)
                for (name,) in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
            }
            has_old_name = any(name.startswith("costing_l0_assembly_") for name in present)
            wrong_unique = cls._assembly_main_uses_part_number_unique(conn)
            if has_old_name or wrong_unique:
                cls._drop_assembly_cost_result_tables(conn)
                logger.info("总成核价表结构不正确，已删表；create_all 将按 source_node_id 重建")
                return
            cls._ensure_assembly_cost_sqlite_columns(conn)

    @classmethod
    def _ensure_assembly_cost_sqlite_columns(cls, conn: Connection) -> None:
        """create_all 不会给已有表加列时补列。"""
        from sqlalchemy import text

        main = "costing_assembly_costs"
        items = "costing_assembly_cost_items"
        logs = "costing_assembly_cost_calc_logs"
        main_cols = cls._table_column_names(conn, main, is_sqlite=True)
        if not main_cols:
            return
        add_cols = [
            ("source_node_id", "INTEGER NOT NULL DEFAULT 0"),
            ("level", "SMALLINT NOT NULL DEFAULT 0"),
            ("is_tree_root", "BOOLEAN NOT NULL DEFAULT 1"),
            ("parent_node_id", "INTEGER"),
            ("root_part_number", "VARCHAR(50)"),
            ("root_part_name", "VARCHAR(200)"),
            ("procurement_object_id", "INTEGER"),
            ("object_kind", "VARCHAR(50)"),
            ("should_cost", "NUMERIC(14, 4) NOT NULL DEFAULT 0"),
            ("vendor_quote", "NUMERIC(14, 4)"),
            ("gap_amount", "NUMERIC(14, 4)"),
            ("vendor_name", "VARCHAR(100)"),
        ]
        for name, ddl in add_cols:
            if name not in main_cols:
                conn.execute(text(f"ALTER TABLE {main} ADD COLUMN {name} {ddl}"))

        item_cols = cls._table_column_names(conn, items, is_sqlite=True)
        if item_cols and "node_level" not in item_cols:
            conn.execute(
                text(f"ALTER TABLE {items} ADD COLUMN node_level INTEGER NOT NULL DEFAULT 0")
            )
        if item_cols and "level_label" in item_cols:
            conn.execute(text(f"ALTER TABLE {items} DROP COLUMN level_label"))

        log_cols = cls._table_column_names(conn, logs, is_sqlite=True)
        if log_cols and "subject_total" not in log_cols and "l0_total" in log_cols:
            conn.execute(text(f"ALTER TABLE {logs} RENAME COLUMN l0_total TO subject_total"))
        elif log_cols and "subject_total" not in log_cols:
            conn.execute(
                text(f"ALTER TABLE {logs} ADD COLUMN subject_total INTEGER NOT NULL DEFAULT 0")
            )
        log_cols = cls._table_column_names(conn, logs, is_sqlite=True)
        if log_cols and "detail_text" not in log_cols:
            conn.execute(
                text(f"ALTER TABLE {logs} ADD COLUMN detail_text TEXT NOT NULL DEFAULT ''")
            )
        if log_cols and "detail_json" not in log_cols:
            conn.execute(text(f"ALTER TABLE {logs} ADD COLUMN detail_json TEXT"))

    _ASSEMBLY_COST_DROP_ORDER = (
        "costing_assembly_cost_items",
        "costing_l0_assembly_cost_items",
        "costing_assembly_cost_indirects",
        "costing_l0_assembly_cost_indirects",
        "costing_assembly_costs",
        "costing_l0_assembly_costs",
        "costing_assembly_cost_calc_logs",
        "costing_l0_assembly_cost_calc_logs",
    )

    @staticmethod
    def _sqlite_table_create_sql(conn: Connection, table_name: str) -> str:
        from sqlalchemy import text

        row = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name = :name"),
            {"name": table_name},
        ).fetchone()
        if row is None or row[0] is None:
            return ""
        return str(row[0])

    @classmethod
    def _sqlite_unique_index_columns(cls, conn: Connection, table_name: str) -> list[list[str]]:
        from sqlalchemy import text

        indexes = conn.execute(text(f'PRAGMA index_list("{table_name}")')).fetchall()
        result: list[list[str]] = []
        for row in indexes:
            is_unique = bool(row[2])
            if not is_unique:
                continue
            index_name = str(row[1])
            cols = [
                str(info[2])
                for info in conn.execute(text(f'PRAGMA index_info("{index_name}")')).fetchall()
            ]
            if cols:
                result.append(cols)
        return result

    @classmethod
    def _assembly_main_uses_part_number_unique(cls, conn: Connection) -> bool:
        """表内 UNIQUE(…, part_number) 无法用 DROP INDEX 去掉。"""
        sql = cls._sqlite_table_create_sql(conn, "costing_assembly_costs")
        if not sql:
            return False
        compact = " ".join(sql.split())
        if "uix_l0_assembly_cost_scope_part" in compact:
            return True
        if "UNIQUE (year, month, location, vehicle_model, bom_version, part_number)" in compact:
            return True
        for cols in cls._sqlite_unique_index_columns(conn, "costing_assembly_costs"):
            if cols[-1] == "part_number" and "source_node_id" not in cols:
                return True
        return False

    @classmethod
    def _drop_assembly_cost_result_tables(cls, conn: Connection) -> None:
        from sqlalchemy import text

        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table_name in cls._ASSEMBLY_COST_DROP_ORDER:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        conn.execute(text("PRAGMA foreign_keys=ON"))

    @classmethod
    def _remap_assembly_cost_permissions(cls, engine: Engine) -> None:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        if "user_permissions" not in set(inspector.get_table_names()):
            return
        old_frag = "l0-assembly-cost"
        new_frag = "assembly-cost"
        remapped = 0
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, user_id, permission_code FROM user_permissions "
                    "WHERE permission_code LIKE :pattern"
                ),
                {"pattern": f"%{old_frag}%"},
            ).fetchall()
            if not rows:
                return
            existing = {
                (int(user_id), str(code))
                for user_id, code in conn.execute(
                    text("SELECT user_id, permission_code FROM user_permissions")
                ).fetchall()
            }
            for row_id, user_id, code in rows:
                new_code = str(code).replace(old_frag, new_frag)
                key = (int(user_id), new_code)
                if key in existing:
                    conn.execute(
                        text("DELETE FROM user_permissions WHERE id = :row_id"),
                        {"row_id": row_id},
                    )
                    continue
                conn.execute(
                    text(
                        "UPDATE user_permissions SET permission_code = :new_code "
                        "WHERE id = :row_id"
                    ),
                    {"new_code": new_code, "row_id": row_id},
                )
                existing.add(key)
                remapped += 1
        if remapped:
            logger.info("已 remap 总成核价权限码 %s 条", remapped)

    @classmethod
    def _migrate_welding_fee_tables(cls, engine: Engine) -> None:
        """旧三表改名到 bom_welding_fees*，须在 create_all 之前执行。"""
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        old_fee, new_fee = "bom_l0_welding_fees", "bom_welding_fees"
        old_item, new_item = "bom_l0_welding_fee_items", "bom_welding_fee_items"
        old_log, new_log = "bom_l0_welding_fee_calc_logs", "bom_welding_fee_calc_logs"
        if old_fee not in tables:
            return

        with engine.begin() as conn:
            if new_fee in tables:
                new_count = int(conn.execute(text(f"SELECT COUNT(*) FROM {new_fee}")).scalar() or 0)
                if new_count > 0:
                    logger.warning("焊接费新旧表同时存在且新表非空，跳过改名")
                    return
                conn.execute(text(f"DROP TABLE IF EXISTS {new_item}"))
                conn.execute(text(f"DROP TABLE IF EXISTS {new_log}"))
                conn.execute(text(f"DROP TABLE IF EXISTS {new_fee}"))
                logger.info("已删除空的新焊接费表，准备从旧表改名")

            cls._ensure_legacy_welding_fee_columns(conn, old_fee)
            conn.execute(text(f"ALTER TABLE {old_fee} RENAME TO {new_fee}"))
            if old_item in tables:
                if new_item in tables:
                    conn.execute(text(f"DROP TABLE IF EXISTS {new_item}"))
                conn.execute(text(f"ALTER TABLE {old_item} RENAME TO {new_item}"))
            if old_log in tables:
                if new_log in tables:
                    conn.execute(text(f"DROP TABLE IF EXISTS {new_log}"))
                conn.execute(text(f"ALTER TABLE {old_log} RENAME TO {new_log}"))
            logger.info("焊接费旧表已改名为 bom_welding_fees*")

    @staticmethod
    def _table_column_names(conn: Connection, table_name: str, *, is_sqlite: bool) -> set[str]:
        from sqlalchemy import text

        if is_sqlite:
            rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            return {str(row[1]) for row in rows}
        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :table_name"
            ),
            {"table_name": table_name},
        ).fetchall()
        return {str(row[0]) for row in rows}

    @classmethod
    def _ensure_legacy_welding_fee_columns(cls, conn: Connection, table_name: str) -> None:
        from sqlalchemy import text

        is_sqlite = conn.dialect.name == "sqlite"
        cols = cls._table_column_names(conn, table_name, is_sqlite=is_sqlite)
        if "weld_info_raw" not in cols:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN weld_info_raw TEXT"))
        if "other_fee" not in cols:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN other_fee NUMERIC(14, 4)"))
        if "final_l0_welding_fee" not in cols and "final_welding_fee" not in cols:
            conn.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN final_l0_welding_fee NUMERIC(14, 4)")
            )
            if "total_l0_welding_fee" in cols:
                conn.execute(
                    text(
                        f"UPDATE {table_name} SET final_l0_welding_fee = total_l0_welding_fee "
                        "WHERE final_l0_welding_fee IS NULL"
                    )
                )
        if "remark" not in cols:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN remark TEXT"))

    @classmethod
    def _ensure_welding_fee_columns(cls, engine: Engine) -> None:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        if "bom_welding_fees" not in set(inspector.get_table_names()):
            return
        is_sqlite = str(engine.url).startswith("sqlite")
        existing_indexes = {
            str(idx.get("name") or "") for idx in inspector.get_indexes("bom_welding_fees")
        }
        with engine.begin() as conn:
            cols = cls._table_column_names(conn, "bom_welding_fees", is_sqlite=is_sqlite)
            if "level" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE bom_welding_fees "
                        "ADD COLUMN level SMALLINT NOT NULL DEFAULT 0"
                    )
                )
                logger.info("已为 bom_welding_fees 追加列 level")
            if "total_welding_fee" not in cols and "total_l0_welding_fee" in cols:
                conn.execute(
                    text(
                        "ALTER TABLE bom_welding_fees "
                        "RENAME COLUMN total_l0_welding_fee TO total_welding_fee"
                    )
                )
            if "final_welding_fee" not in cols and "final_l0_welding_fee" in cols:
                conn.execute(
                    text(
                        "ALTER TABLE bom_welding_fees "
                        "RENAME COLUMN final_l0_welding_fee TO final_welding_fee"
                    )
                )
            if "ix_bom_welding_fee_scope_level" not in existing_indexes:
                conn.execute(
                    text(
                        "CREATE INDEX ix_bom_welding_fee_scope_level "
                        "ON bom_welding_fees (year, location, vehicle_model, bom_version, level)"
                    )
                )

    @classmethod
    def _ensure_vehicle_model_child_fks(cls, engine: Engine) -> None:
        """已有 SQLite 表补 (location, vehicle_model) → vehicle_models 复合外键。"""
        if not str(engine.url).startswith("sqlite"):
            return
        from sqlalchemy import inspect

        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        if "vehicle_models" not in table_names:
            return
        from app.models.bom.node import BomSnapshot
        from app.models.bom.packaging_transport_fee import BomPackagingTransportFee
        from app.models.stamping.die import StampingDiePart
        from app.models.stamping.die_unit_price import StampingDieUnitPrice
        from app.models.stamping.gauge_fee import StampingGaugeFee
        from app.models.stamping.part import StampingPart

        pending = [
            name
            for name in (
                StampingPart.__tablename__,
                StampingDiePart.__tablename__,
                StampingDieUnitPrice.__tablename__,
                StampingGaugeFee.__tablename__,
                BomSnapshot.__tablename__,
                BomPackagingTransportFee.__tablename__,
            )
            if name in table_names
        ]
        if not pending:
            return

        with engine.connect() as conn:
            autocommit = conn.execution_options(isolation_level="AUTOCOMMIT")
            missing = [
                name for name in pending if not cls._sqlite_has_vehicle_model_fk(autocommit, name)
            ]
            if not missing:
                return
            orphans = cls._sqlite_vehicle_model_orphan_pairs(autocommit, missing)
            if orphans:
                detail = "；".join(
                    f"{table} {location}/{code}" for table, location, code in orphans
                )
                raise RuntimeError(
                    "无法给项目下一跳加外键：下列 (基地, 项目) 不在 vehicle_models 中。"
                    "删掉脏行或按正确口径重传，禁止批量改写业务列。"
                    f" {detail}"
                )
            autocommit.exec_driver_sql("PRAGMA foreign_keys=OFF")
            try:
                for table_name in missing:
                    cls._sqlite_rebuild_table(autocommit, table_name)
                    logger.info("已为 %s 补项目复合外键", table_name)
            finally:
                autocommit.exec_driver_sql("PRAGMA foreign_keys=ON")

    @staticmethod
    def _sqlite_has_vehicle_model_fk(conn: Connection, table_name: str) -> bool:
        from sqlalchemy import text

        rows = conn.execute(text(f'PRAGMA foreign_key_list("{table_name}")')).fetchall()
        grouped: dict[int, set[tuple[str, str]]] = {}
        for row in rows:
            if str(row[2]) != "vehicle_models":
                continue
            grouped.setdefault(int(row[0]), set()).add((str(row[3]), str(row[4])))
        expected = {("location", "location"), ("vehicle_model", "vehicle_model")}
        return any(pairs == expected for pairs in grouped.values())

    @staticmethod
    def _sqlite_vehicle_model_orphan_pairs(
        conn: Connection,
        table_names: list[str],
    ) -> list[tuple[str, str, str]]:
        from sqlalchemy import text

        found: list[tuple[str, str, str]] = []
        for table_name in table_names:
            rows = conn.execute(
                text(
                    f'SELECT DISTINCT location, vehicle_model FROM "{table_name}" '
                    "EXCEPT "
                    "SELECT location, vehicle_model FROM vehicle_models"
                )
            ).fetchall()
            for location, vehicle_model in rows:
                found.append((table_name, str(location), str(vehicle_model)))
        return found

    @classmethod
    def _sqlite_rebuild_table(cls, conn: Connection, table_name: str) -> None:
        from sqlalchemy import text
        from sqlalchemy.schema import CreateTable

        table = Base.metadata.tables.get(table_name)
        if table is None:
            raise RuntimeError(f"metadata 中没有表 {table_name}，无法补外键")
        tmp_name = f"{table_name}__vm_fk"
        conn.execute(text(f'DROP TABLE IF EXISTS "{tmp_name}"'))
        compiled = str(CreateTable(table).compile(dialect=conn.dialect)).strip()
        quoted = f'CREATE TABLE "{table_name}"'
        plain = f"CREATE TABLE {table_name}"
        if compiled.startswith(quoted):
            create_sql = f'CREATE TABLE "{tmp_name}"' + compiled[len(quoted) :]
        elif compiled.startswith(plain):
            create_sql = f"CREATE TABLE {tmp_name}" + compiled[len(plain) :]
        else:
            raise RuntimeError(f"无法重写 {table_name} 的 CREATE TABLE")
        conn.execute(text(create_sql))
        columns = ", ".join(f'"{column.name}"' for column in table.columns)
        conn.execute(
            text(f'INSERT INTO "{tmp_name}" ({columns}) SELECT {columns} FROM "{table_name}"')
        )
        conn.execute(text(f'DROP TABLE "{table_name}"'))
        conn.execute(text(f'ALTER TABLE "{tmp_name}" RENAME TO "{table_name}"'))
        for index in table.indexes:
            index.create(bind=conn)

    @classmethod
    def _remap_welding_fee_permissions(cls, engine: Engine) -> None:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        if "user_permissions" not in set(inspector.get_table_names()):
            return
        old_frag = "bom-l0-welding-fee"
        new_frag = "bom-welding-fee"
        remapped = 0
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, user_id, permission_code FROM user_permissions "
                    "WHERE permission_code LIKE :pattern"
                ),
                {"pattern": f"%{old_frag}%"},
            ).fetchall()
            if not rows:
                return
            existing = {
                (int(user_id), str(code))
                for user_id, code in conn.execute(
                    text("SELECT user_id, permission_code FROM user_permissions")
                ).fetchall()
            }
            for row_id, user_id, code in rows:
                new_code = str(code).replace(old_frag, new_frag)
                key = (int(user_id), new_code)
                if key in existing:
                    conn.execute(
                        text("DELETE FROM user_permissions WHERE id = :row_id"),
                        {"row_id": row_id},
                    )
                    continue
                conn.execute(
                    text(
                        "UPDATE user_permissions SET permission_code = :new_code "
                        "WHERE id = :row_id"
                    ),
                    {"new_code": new_code, "row_id": row_id},
                )
                existing.add(key)
                remapped += 1
        if remapped:
            logger.info("已 remap 焊接费权限码 %s 条", remapped)

    @staticmethod
    def _backfill_offal_from_sheet_type(conn: Connection, part_table: str) -> None:
        """按与 Parser 相同规则，从已入库料片式样回填利废并改写式样。"""
        from sqlalchemy import text

        from app.common.offal_nested import parse_offal_from_sheet_type

        rows = conn.execute(text(f"SELECT id, sheet_type FROM {part_table}")).fetchall()
        update_sql = text(
            f"UPDATE {part_table} "
            "SET is_offal_nested = :is_offal_nested, "
            "offal_source = :offal_source, "
            "sheet_type = :sheet_type "
            "WHERE id = :id"
        )
        for row in rows:
            parsed = parse_offal_from_sheet_type(row.sheet_type)
            if not parsed.is_offal_nested and parsed.sheet_type == row.sheet_type:
                continue
            conn.execute(
                update_sql,
                {
                    "id": row.id,
                    "is_offal_nested": 1 if parsed.is_offal_nested else 0,
                    "offal_source": parsed.offal_source,
                    "sheet_type": parsed.sheet_type,
                },
            )


class AuxiliaryDatabaseConfig:
    """
    辅助数据库配置（无 Redis 时的旁路存储）。

    承载：异步任务进度、登录 Token 等短生命周期数据。
    """

    _engine: Engine | None = None
    _session_factory: sessionmaker[Session] | None = None

    @classmethod
    def get_engine(cls) -> Engine:
        if cls._engine is None:
            cls._engine = _create_engine_for_url(
                settings.AUXILIARY_DATABASE_URL,
                label="辅助库",
            )
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> sessionmaker[Session]:
        if cls._session_factory is None:
            engine = cls.get_engine()
            cls._session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return cls._session_factory

    @classmethod
    def create_tables(cls) -> None:
        import app.models.async_task
        import app.models.settings  # noqa: F401

        engine = cls.get_engine()
        AuxiliaryBase.metadata.create_all(bind=engine)
        logger.info("辅助库表创建完成")


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：主业务 Session。"""
    session_factory = DatabaseConfig.get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_auxiliary_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：辅助库 Session（async_tasks / user_tokens 等）。"""
    session_factory = AuxiliaryDatabaseConfig.get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
