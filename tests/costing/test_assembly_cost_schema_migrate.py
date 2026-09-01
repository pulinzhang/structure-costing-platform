"""总成核价主表：去掉零件号唯一，按 BOM 节点唯一。"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

import app.models  # noqa: F401  注册表
from app.database import Base, DatabaseConfig


def _old_main_ddl() -> str:
    return """
    CREATE TABLE costing_assembly_costs (
        id INTEGER NOT NULL PRIMARY KEY,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        location VARCHAR(50) NOT NULL,
        vehicle_model VARCHAR(50) NOT NULL,
        bom_version VARCHAR(20) NOT NULL,
        part_number VARCHAR(50) NOT NULL,
        part_name VARCHAR(200),
        supply_qty NUMERIC(12, 4) NOT NULL DEFAULT 1,
        stamping_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
        purchased_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
        bundle_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
        material_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
        welding_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
        welding_other_fee NUMERIC(14, 4) NOT NULL DEFAULT 0,
        total_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
        unit_transport_fee NUMERIC(14, 4) NOT NULL DEFAULT 0,
        warehouse_bundling_fee NUMERIC(14, 4) NOT NULL DEFAULT 0,
        finished_finance_fee NUMERIC(14, 4) NOT NULL DEFAULT 0,
        finished_management_fee NUMERIC(14, 4) NOT NULL DEFAULT 0,
        finished_scrap_fee NUMERIC(14, 4) NOT NULL DEFAULT 0,
        finished_pretax_profit_fee NUMERIC(14, 4) NOT NULL DEFAULT 0,
        gauge_alloc_fee NUMERIC(14, 4) NOT NULL DEFAULT 0,
        fixture_alloc_fee NUMERIC(14, 4) NOT NULL DEFAULT 0,
        allocation_fee_total NUMERIC(14, 4) NOT NULL DEFAULT 0,
        indirect_amount NUMERIC(14, 4) NOT NULL DEFAULT 0,
        grand_total NUMERIC(14, 4) NOT NULL DEFAULT 0,
        finance_rate NUMERIC(8, 6) NOT NULL DEFAULT 0,
        management_rate NUMERIC(8, 6) NOT NULL DEFAULT 0,
        scrap_rate NUMERIC(8, 6) NOT NULL DEFAULT 0,
        pretax_profit_rate NUMERIC(8, 6) NOT NULL DEFAULT 0,
        calc_status VARCHAR(20) NOT NULL DEFAULT 'ok',
        missing_leaf_count INTEGER NOT NULL DEFAULT 0,
        audit_status VARCHAR(20) NOT NULL DEFAULT 'pending',
        created_at DATETIME NOT NULL,
        created_by VARCHAR(50),
        updated_at DATETIME NOT NULL,
        updated_by VARCHAR(50),
        CONSTRAINT uix_l0_assembly_cost_scope_part UNIQUE (
            year, month, location, vehicle_model, bom_version, part_number
        )
    )
    """


def test_part_number_unique_rebuilds_to_source_node_id(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'assembly.db'}")
    with engine.begin() as conn:
        conn.execute(text(_old_main_ddl()))
        conn.execute(
            text(
                "INSERT INTO costing_assembly_costs ("
                "year, month, location, vehicle_model, bom_version, part_number, "
                "created_at, updated_at"
                ") VALUES (2026, 1, '芜湖', 'T13J', 'D/09', '551001137AA', "
                "'2026-01-01', '2026-01-01')"
            )
        )
        assert conn.execute(text("SELECT COUNT(*) FROM costing_assembly_costs")).scalar() == 1

    DatabaseConfig._migrate_assembly_cost_tables(engine)
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        sql = conn.execute(
            text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='costing_assembly_costs'"
            )
        ).scalar_one()
        compact = " ".join(str(sql).split())
        assert "uix_l0_assembly_cost_scope_part" not in compact
        assert "source_node_id" in compact
        assert (
            "UNIQUE (year, month, location, vehicle_model, bom_version, source_node_id)" in compact
            or "uix_assembly_cost_scope_node" in compact
        )
        assert conn.execute(text("SELECT COUNT(*) FROM costing_assembly_costs")).scalar() == 0

    from datetime import datetime

    from sqlalchemy.orm import Session

    from app.models.costing.assembly_cost import AssemblyCost

    def _card(source_node_id: int) -> AssemblyCost:
        return AssemblyCost(
            year=2026,
            month=1,
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            part_number="551001137AA",
            source_node_id=source_node_id,
            level=1,
            is_tree_root=False,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

    db = Session(engine)
    try:
        db.add(_card(10))
        db.add(_card(11))
        db.commit()
        assert db.query(AssemblyCost).count() == 2
        db.add(_card(10))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()
        engine.dispose()
