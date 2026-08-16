"""
种子数据脚本：把 2026 年冲压冲次单价写入数据库
- 默认基地：青岛
- 价格按四舍五入保留 3 位小数
- 默认幂等（已存在 (location, year, tonnage) 跳过）
- --overwrite 时覆盖已有价格，并删除种子中不存在的吨位
- --dry-run 只打印，不写入

用法（仓库根目录）::

    python -X utf8 -m scripts.seed_tonnage_price_2026
    python -X utf8 -m scripts.seed_tonnage_price_2026 --dry-run
"""

from __future__ import annotations

import argparse
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import Base
from app.models import StampingTonnagePrice


def _round3(value: float) -> Decimal:
    """四舍五入保留 3 位小数"""
    return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


# 2026 年冲次单价原始数据（吨位 T → 元/次），导入前统一保留 3 位小数
SEED_2026_RAW = [
    (40, 0.046),
    (60, 0.053),
    (63, 0.053),
    (80, 0.069),
    (100, 0.085),
    (110, 0.131),
    (125, 0.131),
    (160, 0.131),
    (200, 0.188),
    (250, 0.253),
    (315, 0.357),
    (400, 0.5643),
    (500, 0.62244),
    (630, 0.71345),
    (800, 1.026),
    (1000, 1.2825),
    (1200, 1.539),
    (1250, 1.6036),
    (1300, 1.66725),
    (1500, 1.92375),
    (1600, 2.052),
    (2000, 2.565),
    (2400, 3.078),
    (2500, 3.20625),
]

SEED_2026 = [(tonnage, _round3(price)) for tonnage, price in SEED_2026_RAW]

YEAR = 2026
LOCATION = "青岛"


def make_session() -> Session:
    engine = create_engine(settings.DATABASE_URL, future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def existing_records(session: Session, location: str, year: int) -> list[StampingTonnagePrice]:
    return (
        session.query(StampingTonnagePrice)
        .filter(
            StampingTonnagePrice.location == location,
            StampingTonnagePrice.year == year,
        )
        .order_by(StampingTonnagePrice.tonnage)
        .all()
    )


def run(*, dry_run: bool, overwrite: bool, location: str) -> None:
    session = make_session()
    try:
        existing = existing_records(session, location, YEAR)
        existing_map = {r.tonnage: Decimal(str(r.price_per_stroke)) for r in existing}

        seed_map = dict(SEED_2026)

        inserted: list[tuple[int, float]] = []
        updated: list[tuple[int, float]] = []
        skipped: list[tuple] = []
        deleted: list[int] = []

        if overwrite and existing and not dry_run:
            for r in existing:
                if r.tonnage not in seed_map:
                    deleted.append(r.tonnage)
            if deleted:
                session.query(StampingTonnagePrice).filter(
                    StampingTonnagePrice.location == location,
                    StampingTonnagePrice.year == YEAR,
                    StampingTonnagePrice.tonnage.in_(list(deleted)),
                ).delete(synchronize_session=False)
                session.commit()
            existing = existing_records(session, location, YEAR)
            existing_map = {r.tonnage: Decimal(str(r.price_per_stroke)) for r in existing}

        for tonnage, price in seed_map.items():
            old_price = existing_map.get(tonnage)
            if old_price is None:
                if not dry_run:
                    session.add(StampingTonnagePrice(
                        location=location,
                        year=YEAR,
                        tonnage=tonnage,
                        price_per_stroke=price,
                    ))
                inserted.append((tonnage, float(price)))
            elif old_price != price:
                if dry_run:
                    skipped.append((tonnage, float(old_price), float(price), "would update"))
                elif overwrite:
                    rec = (
                        session.query(StampingTonnagePrice)
                        .filter(
                            StampingTonnagePrice.location == location,
                            StampingTonnagePrice.year == YEAR,
                            StampingTonnagePrice.tonnage == tonnage,
                        )
                        .first()
                    )
                    assert rec is not None
                    rec.price_per_stroke = price
                    updated.append((tonnage, float(price)))
                else:
                    skipped.append(
                        (tonnage, float(old_price), float(price), "different price, kept")
                    )
            else:
                skipped.append((tonnage, float(old_price), float(price), "same"))

        if not dry_run:
            session.commit()

        mode = "DRY-RUN" if dry_run else "WRITE"
        print(
            f"[{mode}] location={location} year={YEAR} "
            f"seed_count={len(SEED_2026)} existing={len(existing)}"
        )
        print(f"  inserted   ({len(inserted)}): {inserted}")
        print(f"  updated    ({len(updated)}):  {updated}")
        skipped_preview = skipped if len(skipped) <= 8 else skipped[:8] + ["..."]
        print(f"  skipped    ({len(skipped)}):  {skipped_preview}")
        print(f"  deleted    ({len(deleted)}):  {deleted}")
        print("  prices (3dp):")
        for tonnage, price in SEED_2026:
            print(f"    {tonnage}T  {price} 元/次")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--location", default=LOCATION, help="采购基地，默认青岛")
    args = parser.parse_args()
    run(dry_run=args.dry_run, overwrite=args.overwrite, location=args.location)
