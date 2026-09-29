"""存量加减价里的历史表头要能回填到已有钢厂。"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.bootstrap.steel_mill_schema import ensure_steel_mill_fact_schema


def test_policy_historical_spellings_fill_mill_id() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE steel_mills ("
                "id INTEGER PRIMARY KEY, abbreviation VARCHAR(50) NOT NULL, "
                "full_name VARCHAR(50) NOT NULL, is_enabled BOOLEAN NOT NULL, "
                "sort_order INTEGER NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE steel_mill_aliases ("
                "alias VARCHAR(50) PRIMARY KEY, steel_mill_id INTEGER NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO steel_mills (id, abbreviation, full_name, is_enabled, sort_order) "
                "VALUES (1, '鞍神', '鞍神', 1, 1), (2, '宝钢', '宝钢', 1, 2), "
                "(3, '首钢', '首钢', 1, 3), (4, '山钢', '山钢', 1, 4)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE steel_price_policies ("
                "id INTEGER PRIMARY KEY, year INTEGER NOT NULL, month INTEGER NOT NULL, "
                "steel_mill VARCHAR(100) NOT NULL, category_name VARCHAR(100) NOT NULL, "
                "policy_type VARCHAR(20) NOT NULL, grade_type VARCHAR(20), "
                "grade_value VARCHAR(100), base_thickness NUMERIC(5, 2), "
                "excel_filename VARCHAR(255), created_at DATETIME NOT NULL, "
                "created_by VARCHAR(50), updated_at DATETIME NOT NULL, updated_by VARCHAR(50))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO steel_price_policies ("
                "year, month, steel_mill, category_name, policy_type, grade_value, "
                "base_thickness, created_at, updated_at) VALUES "
                "(2024, 11, '鞍神(新)', '冷轧钢', 'THICKNESS_WIDTH', '2.0＜T≤2.3', NULL, "
                "'2024-11-01', '2024-11-01'), "
                "(2024, 2, '宝钢 (2)', '冷轧钢', 'THICKNESS', '冷轧钢', 1, "
                "'2024-02-01', '2024-02-01'), "
                "(2024, 2, '首钢 (2)', '冷轧钢', 'THICKNESS', '冷轧钢', 1, "
                "'2024-02-01', '2024-02-01'), "
                "(2024, 2, '山钢 (2)', '镀锌钢', 'THICKNESS', '镀锌钢', 1, "
                "'2024-02-01', '2024-02-01')"
            )
        )

    ensure_steel_mill_fact_schema(engine)

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT steel_mill, steel_mill_id FROM steel_price_policies ORDER BY id")
        ).all()
        aliases = {
            str(row[0])
            for row in connection.execute(text("SELECT alias FROM steel_mill_aliases")).all()
        }
    assert rows == [("鞍神", 1), ("宝钢", 2), ("首钢", 3), ("山钢", 4)]
    assert {"鞍神(新)", "宝钢 (2)", "首钢 (2)", "山钢 (2)"} <= aliases
    engine.dispose()
