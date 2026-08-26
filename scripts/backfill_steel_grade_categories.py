"""
上线回填：从现网基价去重 (grade, category_name) 写入牌号分类档案。

幂等：已有牌号不改大类；待分类可被基价大类认领；冲突只打印不覆盖。

用法（仓库根目录）::

    python -X utf8 -m scripts.backfill_steel_grade_categories
    python -X utf8 -m scripts.backfill_steel_grade_categories --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.common.audit import SYSTEM_USER
from app.database import DatabaseConfig
from app.models.yishiyiyi.steel_grade_category import SteelGradeCategory
from app.services.yishiyiyi.steel_grade_category import SteelGradeCategoryService

logger = logging.getLogger("scripts.backfill_steel_grade_categories")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从基价回填牌号分类档案")
    parser.add_argument("--dry-run", action="store_true", help="只统计将写入的去重行，不落库")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    service = SteelGradeCategoryService()
    try:
        SteelGradeCategory.__table__.create(bind=db.get_bind(), checkfirst=True)
        pairs = service.base_price_repository.list_distinct_grade_categories(db)
        logger.info("基价去重牌号 %d 条", len(pairs))
        if args.dry_run:
            logger.info("[dry-run] 不写入 steel_grade_categories")
            return 0
        result = service.backfill_from_base_prices(db, SYSTEM_USER)
        logger.info(
            "回填完成 inserted=%d claimed=%d skipped=%d conflicts=%d",
            result.inserted_count,
            result.claimed_count,
            result.skipped_count,
            len(result.conflicts or []),
        )
        if result.conflicts:
            for line in result.conflicts[:50]:
                logger.info("冲突: %s", line)
            extra = len(result.conflicts) - 50
            if extra > 0:
                logger.info("…另有 %d 条冲突未打印", extra)
        return 0
    except Exception:
        logger.exception("回填失败")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
