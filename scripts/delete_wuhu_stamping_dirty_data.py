"""删除芜湖冲压工艺脏数据（未知车型 / 空冲压工厂）。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import DatabaseConfig  # noqa: E402
from app.repositories.stamping.stamping_part_repository import StampingPartRepository  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scripts.delete_wuhu_stamping")

LOCATION = "芜湖"
SUPPLIER = ""
VEHICLE_MODEL = "未知车型"
VERSION = "V1"


def main() -> None:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        scopes = conn.execute(
            text(
                "SELECT location, stamping_supplier, vehicle_model, version, COUNT(*) "
                "FROM stamping_parts WHERE location = :loc "
                "GROUP BY location, stamping_supplier, vehicle_model, version"
            ),
            {"loc": LOCATION},
        ).fetchall()
        logger.info("芜湖 stamping_parts scopes before delete: %s", scopes)

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    repo = StampingPartRepository()
    try:
        deleted = repo.delete_by_scope(
            db,
            location=LOCATION,
            stamping_supplier=SUPPLIER,
            vehicle_model=VEHICLE_MODEL,
            version=VERSION,
        )
        db.commit()
        logger.info("已删除芜湖冲压工艺: %d 个零件（含工序/拼焊子片）", deleted)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    with engine.connect() as conn:
        remaining = conn.execute(
            text("SELECT COUNT(*) FROM stamping_parts WHERE location = :loc"),
            {"loc": LOCATION},
        ).scalar()
        logger.info("芜湖 stamping_parts remaining: %s", remaining)


if __name__ == "__main__":
    main()
