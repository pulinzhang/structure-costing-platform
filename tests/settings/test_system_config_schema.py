"""存量 system_configs 启动时补三列，已有行带上默认值。"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.bootstrap.system_config_schema import ensure_system_config_schema


def test_ensure_adds_three_columns_with_defaults() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE system_configs ("
                "id INTEGER PRIMARY KEY, "
                "app_name VARCHAR(100) NOT NULL"
                ")"
            )
        )
        connection.execute(text("INSERT INTO system_configs (id, app_name) VALUES (1, '核价')"))

    ensure_system_config_schema(engine)
    ensure_system_config_schema(engine)

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT base_price_month_move_limit, "
                "base_price_processing_fee_limit, "
                "body_panel_max_thickness "
                "FROM system_configs WHERE id = 1"
            )
        ).one()
    assert float(row[0]) == 300
    assert float(row[1]) == 120
    assert float(row[2]) == 3
    engine.dispose()


def test_ensure_skips_when_table_is_missing() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ensure_system_config_schema(engine)
    engine.dispose()
