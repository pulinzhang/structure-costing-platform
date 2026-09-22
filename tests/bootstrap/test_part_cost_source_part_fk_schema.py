"""存量零件核价补 source_part_id 外键：对得上才重建，空或对不上拒绝且不改表。"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.bootstrap.part_cost_source_part_fk_schema import ensure_part_cost_source_part_fk_schema
from app.models.costing.stamping_part_cost import StampingPartCost


def _legacy_ddl(*, nullable_source: bool = False) -> str:
    ddl = str(CreateTable(StampingPartCost.__table__).compile(dialect=sqlite.dialect()))
    lines = [line for line in ddl.splitlines() if line.strip() and "FOREIGN KEY" not in line]
    if lines[-1].strip() == ")":
        lines[-2] = lines[-2].rstrip().rstrip(",")
    ddl = "\n".join(lines)
    if nullable_source:
        ddl = ddl.replace("source_part_id INTEGER NOT NULL", "source_part_id INTEGER", 1)
    return ddl


def _engine(*, nullable_source: bool = False):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE stamping_parts (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO stamping_parts (id) VALUES (1)"))
        connection.execute(text(_legacy_ddl(nullable_source=nullable_source)))
    return engine


def _insert_cost(engine, source_part_id: int) -> None:
    with Session(engine) as db:
        db.add(
            StampingPartCost(
                year=2025,
                month=1,
                location="芜湖",
                stamping_supplier="安庆常庆汽车部件有限公司",
                vehicle_model="T13J",
                version="V1",
                source_part_id=source_part_id,
                part_number="502000001AA",
                created_by="system",
                updated_by="system",
            )
        )
        db.commit()


def test_rebuilds_when_every_source_part_exists() -> None:
    engine = _engine()
    _insert_cost(engine, 1)
    ensure_part_cost_source_part_fk_schema(engine)
    with engine.connect() as connection:
        rows = connection.execute(text("PRAGMA foreign_key_list(stamping_part_costs)")).all()
        referred = {(str(row[2]), str(row[3])) for row in rows}
        assert ("stamping_parts", "source_part_id") in referred
        count = connection.execute(text("SELECT count(id) FROM stamping_part_costs")).scalar()
        assert count == 1
        old = connection.execute(
            text(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='stamping_part_costs__old_fk'"
            )
        ).first()
        assert old is None
    ensure_part_cost_source_part_fk_schema(engine)


def test_refuses_orphans_without_renaming() -> None:
    engine = _engine()
    _insert_cost(engine, 99999)
    try:
        ensure_part_cost_source_part_fk_schema(engine)
        raise AssertionError("orphan rows should refuse startup")
    except Exception as error:
        assert "拒绝重建外键" in str(error)
    with engine.connect() as connection:
        still = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='stamping_part_costs'")
        ).first()
        renamed = connection.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='stamping_part_costs__old_fk'"
            )
        ).first()
        count = connection.execute(text("SELECT count(id) FROM stamping_part_costs")).scalar()
    assert still is not None
    assert renamed is None
    assert count == 1


def test_refuses_null_source_without_renaming() -> None:
    engine = _engine(nullable_source=True)
    _insert_cost(engine, 1)
    with engine.begin() as connection:
        connection.execute(text("UPDATE stamping_part_costs SET source_part_id = NULL"))
    try:
        ensure_part_cost_source_part_fk_schema(engine)
        raise AssertionError("null source should refuse startup")
    except Exception as error:
        assert "拒绝重建外键" in str(error)
    with engine.connect() as connection:
        renamed = connection.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='stamping_part_costs__old_fk'"
            )
        ).first()
        count = connection.execute(text("SELECT count(id) FROM stamping_part_costs")).scalar()
    assert renamed is None
    assert count == 1
