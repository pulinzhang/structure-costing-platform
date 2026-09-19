"""
批量导入 excel_sample 下厚度加减价政策 Excel（开发测试）。

文件名匹配：含「厚度加减价」，或含「一事一议」且不含「发布价格」。
生效期：订单目录名优先（如 25年9月订单10月 → 2025-10），其次文件名括号；
双月如 6月和7月（仅文件名）各导一次。同月多份优先文件名含「厚度加减价」者。

用法::

    python -X utf8 -m scripts.import_policy_thickness_samples
    python -X utf8 -m scripts.import_policy_thickness_samples --dry-run
    python -X utf8 -m scripts.import_policy_thickness_samples --limit 2
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
from app.parsers.yishiyiyi.policy import parse_steel_price_policy_excel
from app.services.yishiyiyi.policy.importing.import_service import SteelPricePolicyImportService

logger = logging.getLogger("scripts.import_policy_thickness_samples")

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "excel_sample" / "25年-26年一事一议价格"


def _is_thickness_policy_filename(name: str) -> bool:
    """厚度加减价样例：明示「厚度加减价」，或「一事一议」且非「发布价格」基准价。"""
    if "发布价格" in name:
        return False
    return "厚度加减价" in name or "一事一议" in name


def _preference_key(path: Path) -> tuple[int, int, int, str]:
    """越小越优先：文件名含厚度加减价 > xlsx > 短名。"""
    name = path.name
    return (
        0 if "厚度加减价" in name else 1,
        0 if path.suffix.lower() == ".xlsx" else 1,
        len(name),
        str(path),
    )


def _iter_sample_jobs(root: Path) -> list[tuple[PolicyEffectivePeriod, Path]]:
    """按生效月择优；同月多文件只留最优先正式稿。"""
    candidates = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not path.name.startswith("~$")
        and _is_thickness_policy_filename(path.name)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导入样例厚度加减价政策 Excel")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="样例根目录")
    parser.add_argument("--dry-run", action="store_true", help="只解析统计，不写库")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个月份，0=不限")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root = args.root
    if not root.is_dir():
        logger.error("目录不存在: %s", root)
        return 1

    jobs = _iter_sample_jobs(root)
    if args.limit > 0:
        jobs = jobs[: args.limit]
    if not jobs:
        logger.error("未找到厚度加减价样例 Excel: %s", root)
        return 1

    logger.info("待处理 %d 个生效月（root=%s）", len(jobs), root)
    import_service = SteelPricePolicyImportService()
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    total_policies = 0
    try:
        for index, (period, path) in enumerate(jobs, start=1):
            content = path.read_bytes()
            import_service.validate_upload(content, path.name)
            result = parse_steel_price_policy_excel(
                content,
                year=period.year,
                month=period.month,
                excel_filename=path.name,
            )
            thickness_count = sum(
                1 for policy in result.policies if policy.policy_type == "THICKNESS"
            )
            width_count = sum(1 for policy in result.policies if policy.policy_type == "WIDTH")
            total_policies += len(result.policies)
            logger.info(
                "[%d/%d] %s → %04d-%02d policies=%d (THICKNESS=%d WIDTH=%d)",
                index,
                len(jobs),
                path.name,
                period.year,
                period.month,
                len(result.policies),
                thickness_count,
                width_count,
            )
            if args.dry_run:
                continue

            import_service.import_from_parser(
                db,
                file_content=content,
                filename=path.name,
                year=period.year,
                month=period.month,
                current_user=SYSTEM_USER,
            )
        if not args.dry_run:
            logger.info(
                "导入完成：生效月 %d 个、累计解析政策头 %d 条",
                len(jobs),
                total_policies,
            )
        else:
            logger.info(
                "[dry-run] 生效月 %d 个、累计政策头 %d 条",
                len(jobs),
                total_policies,
            )
        return 0
    except Exception:
        db.rollback()
        logger.exception("导入失败")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
