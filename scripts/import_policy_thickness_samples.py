"""
批量导入 excel_sample 下含「厚度加减价」的政策 Excel（开发测试）。

文件名括号内年月为入库生效期（期货：订次月原料生效）。

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
from app.common.policy_effective_period import effective_period_from_policy_filename
from app.database import DatabaseConfig
from app.parsers.yishiyiyi.policy import parse_steel_price_policy_excel
from app.services.yishiyiyi.policy.importing.import_service import SteelPricePolicyImportService

logger = logging.getLogger("scripts.import_policy_thickness_samples")

DEFAULT_ROOT = (
    Path(__file__).resolve().parents[1]
    / "excel_sample"
    / "25年-26年一事一议价格"
    / "2026年1月-12月一事一议价格"
)


def _iter_sample_files(root: Path) -> list[Path]:
    files = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and "厚度加减价" in path.name
        and path.suffix.lower() in {".xlsx", ".xls", ".xlsm"}
    ]
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导入样例厚度加减价政策 Excel")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="样例根目录")
    parser.add_argument("--dry-run", action="store_true", help="只解析统计，不写库")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个文件，0=不限")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root = args.root
    if not root.is_dir():
        logger.error("目录不存在: %s", root)
        return 1

    files = _iter_sample_files(root)
    if args.limit > 0:
        files = files[: args.limit]
    if not files:
        logger.error("未找到含「厚度加减价」的 Excel: %s", root)
        return 1

    logger.info("待处理 %d 个文件（root=%s）", len(files), root)
    import_service = SteelPricePolicyImportService()
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    total_policies = 0
    try:
        for index, path in enumerate(files, start=1):
            period = effective_period_from_policy_filename(path.name)
            if period is None:
                logger.warning("[%d/%d] 跳过（无法解析生效期）: %s", index, len(files), path.name)
                continue

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
                len(files),
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
            logger.info("导入完成，累计解析政策头 %d 条", total_policies)
        else:
            logger.info("[dry-run] 累计将导入政策头 %d 条", total_policies)
        return 0
    except Exception:
        db.rollback()
        logger.exception("导入失败")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
