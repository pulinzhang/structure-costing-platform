"""
批量导入 excel_sample 下含「发布价格」的基准价 Excel（开发测试）。

生效期：订单目录名优先（如 25年9月订单10月 → 2025-10），其次文件名括号。
同生效月多份时优先正式稿（非副本 / 非自动保存 / 非 (1)）。
仅价格列月份：附页钢厂 + 上月 (基地,牌号) 承接。

用法::

    python -X utf8 -m scripts.import_base_price_samples
    python -X utf8 -m scripts.import_base_price_samples --dry-run
    python -X utf8 -m scripts.import_base_price_samples --limit 2
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.common.audit import SYSTEM_USER
from app.common.policy_effective_period import (
    PolicyEffectivePeriod,
    effective_periods_from_sample_path,
)
from app.database import DatabaseConfig
from app.parsers.yishiyiyi.base_price.steel_base_price_parser import (
    parse_base_price_excel,
)
from app.services.masterdata.location.service import LocationService
from app.services.yishiyiyi.base_price.importing.service import SteelBasePriceImportService

logger = logging.getLogger("scripts.import_base_price_samples")

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "excel_sample" / "25年-26年一事一议价格"


def _preference_key(path: Path) -> tuple[int, int, int, int, int, str]:
    """越小越优先：正式稿、xlsx、短文件名。"""
    name = path.name
    return (
        1 if "副本" in name else 0,
        1 if "自动保存" in name else 0,
        1 if "(1)" in name or "（1）" in name else 0,
        0 if path.suffix.lower() == ".xlsx" else 1,
        len(name),
        str(path),
    )


def _iter_sample_files(root: Path) -> list[tuple[PolicyEffectivePeriod, Path]]:
    """
    收集含「发布价格」的 Excel；生效期目录优先；同生效月多份取最优先正式稿。
    同名文件可落在不同订单目录（错标文件名），按目录拆成不同生效月，不按文件名去重。
    """
    candidates = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not path.name.startswith("~$")
        and "发布价格" in path.name
        and path.suffix.lower() in {".xlsx", ".xls", ".xlsm"}
    ]

    by_period: dict[tuple[int, int], Path] = {}
    for path in candidates:
        periods = effective_periods_from_sample_path(path, root=root)
        if not periods:
            logger.warning("跳过（无法解析生效期）: %s", path)
            continue
        for period in periods:
            key = (period.year, period.month)
            existing = by_period.get(key)
            if existing is None or _preference_key(path) < _preference_key(existing):
                if existing is not None and existing != path:
                    logger.info(
                        "同月择优：%04d-%02d 用 %s（弃 %s）",
                        period.year,
                        period.month,
                        path.name,
                        existing.name,
                    )
                by_period[key] = path
            elif existing != path:
                logger.info(
                    "同月择优：%04d-%02d 保留 %s（弃 %s）",
                    period.year,
                    period.month,
                    existing.name,
                    path.name,
                )

    return [
        (PolicyEffectivePeriod(year=year, month=month), path)
        for (year, month), path in sorted(by_period.items())
    ]


def _remember_mills(
    cache: dict[tuple[str, str], str],
    records: list[dict[str, object]],
) -> None:
    for record in records:
        location = str(record.get("location") or "").strip()
        grade = str(record.get("grade") or "").strip().replace("//", "/")
        mill = str(record.get("steel_mill") or "").strip()
        if location and grade and mill:
            cache[(location, grade)] = mill


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导入样例基准价「发布价格」Excel")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="样例根目录")
    parser.add_argument("--dry-run", action="store_true", help="只解析统计，不写库")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个月份，0=不限")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root = args.root
    if not root.is_dir():
        logger.error("目录不存在: %s", root)
        return 1

    jobs = _iter_sample_files(root)
    if args.limit > 0:
        jobs = jobs[: args.limit]
    if not jobs:
        logger.error("未找到含「发布价格」的 Excel: %s", root)
        return 1

    logger.info("待处理 %d 个生效月（root=%s）", len(jobs), root)
    import_service = SteelBasePriceImportService()
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    total_rows = 0
    mill_cache: dict[tuple[str, str], str] = {}
    try:
        location_service = LocationService()
        lookup = location_service.enabled_name_lookup(db)
        if not lookup:
            logger.error("没有已启用基地，请先到基地页启用")
            return 1

        for index, (period, path) in enumerate(jobs, start=1):
            content = path.read_bytes()
            parse_result = parse_base_price_excel(
                content,
                location_lookup=lookup,
                carry_mills=mill_cache or None,
            )
            row_count = len(parse_result.records)
            total_rows += row_count
            warn_count = len(parse_result.warnings)
            error_count = len(parse_result.errors)
            logger.info(
                "[%d/%d] %s → %04d-%02d rows=%d warnings=%d errors=%d",
                index,
                len(jobs),
                path.name,
                period.year,
                period.month,
                row_count,
                warn_count,
                error_count,
            )
            for warning in parse_result.warnings[:5]:
                logger.warning("  warn: %s", warning)
            for error in parse_result.errors[:5]:
                logger.error("  error: %s", error)

            _remember_mills(mill_cache, parse_result.records)

            if args.dry_run:
                continue
            if error_count and row_count == 0:
                logger.warning("  跳过写库（无有效行）")
                continue

            result = import_service.import_excel(
                db,
                file_content=content,
                filename=path.name,
                year=period.year,
                month=period.month,
                current_user=SYSTEM_USER,
                carry_mills=mill_cache or None,
            )
            logger.info(
                "  写入 created=%d updated=%d total=%d",
                result.created_count,
                result.updated_count,
                result.total,
            )

        if args.dry_run:
            logger.info("[dry-run] 生效月 %d 个、累计解析行 %d", len(jobs), total_rows)
        else:
            logger.info("导入完成：生效月 %d 个、累计解析行 %d", len(jobs), total_rows)
        return 0
    except Exception:
        db.rollback()
        logger.exception("导入失败")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
