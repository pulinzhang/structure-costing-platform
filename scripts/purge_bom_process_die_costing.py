"""
清空 BOM / 冲压工艺确认 / 模具布点及其下游结果（开发 / 联调重导用）。

含：总成核算、焊接分拆、采购对象、材料清单、加工费、模具费、布点、工艺确认。
加工费 / 模具费因 RESTRICT 挡删上游，一并清掉。

不碰：主数据（基地/项目/供应商）、冲次单价、模具单价、检具费、钢价政策等档案。

用法（仓库根目录）::

    python -X utf8 -m scripts.purge_bom_process_die_costing
    python -X utf8 -m scripts.purge_bom_process_die_costing --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import text

from app.database import DatabaseConfig

logger = logging.getLogger("scripts.purge_bom_process_die_costing")

# 子表 / 下游结果先删，再删上游主数据
DELETE_ORDER: tuple[str, ...] = (
    # 总成核算
    "costing_assembly_cost_items",
    "costing_assembly_cost_indirects",
    "costing_assembly_costs",
    "costing_assembly_cost_calc_logs",
    # 焊接工艺分拆
    "bom_welding_process_breakdown_line",
    "bom_welding_process_breakdown_node",
    "bom_welding_process_breakdown_generate_logs",
    # 采购对象
    "bom_procurement_objects",
    "bom_procurement_object_lists",
    "bom_procurement_object_generate_logs",
    # 材料清单
    "bom_nodes",
    "bom_snapshots",
    # 冲压加工费（RESTRICT → stamping_parts）
    "stamping_process_fee_items",
    "stamping_process_fees",
    "stamping_process_fee_calc_logs",
    # 冲压模具费（RESTRICT → stamping_die_parts）
    "stamping_die_fee_items",
    "stamping_die_fees",
    "stamping_die_fee_calc_logs",
    # 模具布点
    "stamping_die_processes",
    "stamping_die_parts",
    # 冲压工艺确认
    "stamping_processes",
    "stamping_tailor_weld_blanks",
    "stamping_parts",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="清空 BOM / 工艺确认 / 布点及其下游核算结果（开发用）"
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计行数，不删除")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        before: dict[str, int] = {}
        for table_name in DELETE_ORDER:
            count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            before[table_name] = int(count or 0)

        logger.info("待清理（按删除顺序）:")
        for table_name, count in before.items():
            logger.info("  %s: %d", table_name, count)
        logger.info("合计: %d", sum(before.values()))

        if args.dry_run:
            logger.info("[dry-run] 未删除")
            return 0

        deleted: dict[str, int] = {}
        for table_name in DELETE_ORDER:
            result = db.execute(text(f"DELETE FROM {table_name}"))
            deleted[table_name] = int(result.rowcount or 0)
        db.commit()

        logger.info("已删除:")
        for table_name, count in deleted.items():
            if count:
                logger.info("  %s: %d", table_name, count)
        logger.info("合计: %d", sum(deleted.values()))
        return 0
    except Exception:
        db.rollback()
        logger.exception("清理失败")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
