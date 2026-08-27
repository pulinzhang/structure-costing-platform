"""
清空加减价政策历史数据（开发环境）。

删除 steel_price_policies / steel_price_ladder_items 及 file_trace 中政策上传记录。

用法（仓库根目录）::

    python -X utf8 -m scripts.purge_steel_price_policies
    python -X utf8 -m scripts.purge_steel_price_policies --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.database import DatabaseConfig
from app.models.file_trace import UploadFile
from app.models.yishiyiyi.steel_price_policy import SteelPriceLadderItem, SteelPricePolicy

logger = logging.getLogger("scripts.purge_steel_price_policies")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="清空加减价政策表（开发用）")
    parser.add_argument("--dry-run", action="store_true", help="只统计行数，不删除")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        policy_count = db.query(SteelPricePolicy).count()
        item_count = db.query(SteelPriceLadderItem).count()
        trace_count = (
            db.query(UploadFile).filter(UploadFile.file_category == "steel_price_policy").count()
        )
        logger.info(
            "待清理: policies=%d ladder_items=%d file_trace(policy)=%d",
            policy_count,
            item_count,
            trace_count,
        )
        if args.dry_run:
            logger.info("[dry-run] 未删除")
            return 0

        deleted_items = db.query(SteelPriceLadderItem).delete(synchronize_session=False)
        deleted_policies = db.query(SteelPricePolicy).delete(synchronize_session=False)
        deleted_trace = (
            db.query(UploadFile)
            .filter(UploadFile.file_category == "steel_price_policy")
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(
            "已删除 ladder_items=%d policies=%d file_trace=%d",
            deleted_items,
            deleted_policies,
            deleted_trace,
        )
        return 0
    except Exception:
        db.rollback()
        logger.exception("清理失败")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
