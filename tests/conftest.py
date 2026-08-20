"""pytest 公共夹具。"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from app.config import BASE_DIR, settings


@pytest.fixture(scope="session")
def db_file_path() -> Path:
    return BASE_DIR / "data" / "stamping_costing.db"


@pytest.fixture(scope="session")
def db_session(db_file_path: Path) -> Generator[Session, None, None]:
    """只读连接主业务库（开发库），供数据就绪类集成测试使用。"""
    if not db_file_path.exists():
        pytest.skip(f"主库不存在: {db_file_path}")

    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    required = (
        "bom_snapshots",
        "bom_nodes",
        "stamping_part_costs",
        "bom_annual_part_prices",
        "bom_l0_welding_fees",
    )
    missing_tables = [name for name in required if not inspector.has_table(name)]
    if missing_tables:
        pytest.skip(f"缺表，跳过集成模拟: {missing_tables}")

    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
