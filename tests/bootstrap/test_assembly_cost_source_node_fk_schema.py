"""存量总成核价补 source_node_id 外键：对得上才重建，对不上拒绝且不改表。"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.bootstrap.assembly_cost_source_node_fk_schema import (
    ensure_assembly_cost_source_node_fk_schema,
)
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_indirect import AssemblyCostIndirect
from app.models.costing.assembly_cost_item import AssemblyCostItem


def _legacy_ddl(table) -> str:
    ddl = str(CreateTable(table).compile(dialect=sqlite.dialect()))
    lines = [line for line in ddl.splitlines() if line.strip() and "FOREIGN KEY" not in line]
    if lines[-1].strip() == ")":
        lines[-2] = lines[-2].rstrip().rstrip(",")
    return "\n".join(lines)


def _engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE bom_nodes (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO bom_nodes (id) VALUES (1)"))
        connection.execute(text(_legacy_ddl(AssemblyCost.__table__)))
        connection.execute(text(_legacy_ddl(AssemblyCostItem.__table__)))
        connection.execute(text(_legacy_ddl(AssemblyCostIndirect.__table__)))
    return engine


def _insert_cost(engine, source_node_id: int) -> None:
    with Session(engine) as db:
        db.add(
            AssemblyCost(
                year=2025,
                month=1,
                location="芜湖",
                vehicle_model="T13J",
                bom_version="D/09",
                source_node_id=source_node_id,
                part_number="501006870AA",
                created_by="system",
                updated_by="system",
            )
        )
        db.flush()
        db.add(
            AssemblyCostItem(
                assembly_cost_id=db.query(AssemblyCost).one().id,
                part_number="CHILD",
                cost_source="stamping",
            )
        )
        db.add(
            AssemblyCostIndirect(
                assembly_cost_id=db.query(AssemblyCost).one().id,
                code="I1",
                label="运费",
            )
        )
        db.commit()


def test_rebuilds_when_every_source_node_exists() -> None:
    engine = _engine()
    _insert_cost(engine, 1)
    ensure_assembly_cost_source_node_fk_schema(engine)
    with engine.connect() as connection:
        rows = connection.execute(text("PRAGMA foreign_key_list(costing_assembly_costs)")).all()
        referred = {(str(row[2]), str(row[3])) for row in rows}
        assert ("bom_nodes", "source_node_id") in referred
        count = connection.execute(text("SELECT count(id) FROM costing_assembly_costs")).scalar()
        item_count = connection.execute(
            text("SELECT count(id) FROM costing_assembly_cost_items")
        ).scalar()
        indirect_count = connection.execute(
            text("SELECT count(id) FROM costing_assembly_cost_indirects")
        ).scalar()
        assert count == 1
        assert item_count == 1
        assert indirect_count == 1
        old = connection.execute(
            text(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='costing_assembly_costs__old_fk'"
            )
        ).first()
        assert old is None
    ensure_assembly_cost_source_node_fk_schema(engine)


def test_refuses_orphans_without_renaming() -> None:
    engine = _engine()
    _insert_cost(engine, 99999)
    try:
        ensure_assembly_cost_source_node_fk_schema(engine)
        raise AssertionError("orphan rows should refuse startup")
    except Exception as error:
        assert "拒绝重建外键" in str(error)
    with engine.connect() as connection:
        still = connection.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='costing_assembly_costs'"
            )
        ).first()
        renamed = connection.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='costing_assembly_costs__old_fk'"
            )
        ).first()
        count = connection.execute(text("SELECT count(id) FROM costing_assembly_costs")).scalar()
    assert still is not None
    assert renamed is None
    assert count == 1
