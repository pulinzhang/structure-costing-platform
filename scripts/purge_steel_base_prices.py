"""
清空钢材基准价历史数据（开发环境）。

删除 steel_base_prices 及 file_trace 中基准价上传记录。

用法（仓库根目录）::

    python -X utf8 -m scripts.purge_steel_base_prices
    python -X utf8 -m scripts.purge_steel_base_prices --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.database import DatabaseConfig
from app.models.file_trace import UploadFile
from app.models.yishiyiyi.steel_base_price import SteelBasePrice

logger = logging.getLogger("scripts.purge_steel_base_prices")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="清空基准价表（开发用）")
    parser.add_argument("--dry-run", action="store_true", help="只统计行数，不删除")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        price_count = db.query(SteelBasePrice).count()
        trace_count = (
            db.query(UploadFile).filter(UploadFile.file_category == "steel_base_price").count()
        )
        logger.info("待清理: base_prices=%d file_trace(base_price)=%d", price_count, trace_count)
        if args.dry_run:
            logger.info("[dry-run] 未删除")
            return 0

        deleted_prices = db.query(SteelBasePrice).delete(synchronize_session=False)
        deleted_trace = (
            db.query(UploadFile)
            .filter(UploadFile.file_category == "steel_base_price")
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("已删除 base_prices=%d file_trace=%d", deleted_prices, deleted_trace)
        return 0
    except Exception:
        db.rollback()
        logger.exception("清理失败")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
