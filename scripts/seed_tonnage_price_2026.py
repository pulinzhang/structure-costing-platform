"""
种子数据脚本：把 2026 年冲压冲次费率写入数据库
- 价格按四舍五入保留 3 位小数
- 默认幂等（已存在 (year, tonnage) 跳过）
- --overwrite 时覆盖已有价格，并删除种子中不存在的吨位
- --dry-run 只打印，不写入
"""
import argparse
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# 允许在仓库根目录直接运行：把仓库根加入 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models import StampingTonnagePrice


def _round3(value: float) -> Decimal:
    """四舍五入保留 3 位小数"""
    return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


# 2026 年冲次费率原始数据（吨位 T → 元/次），导入前统一保留 3 位小数
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


def make_session():
    engine = create_engine(settings.DATABASE_URL, future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def existing_records(session, year):
    return (
        session.query(StampingTonnagePrice)
        .filter(StampingTonnagePrice.year == year)
        .order_by(StampingTonnagePrice.tonnage)
        .all()
    )


def run(dry_run: bool, overwrite: bool):
    session = make_session()
    try:
        existing = existing_records(session, YEAR)
        existing_map = {r.tonnage: Decimal(str(r.price_per_stroke)) for r in existing}

        seed_map = dict(SEED_2026)

        inserted, updated, skipped, deleted = [], [], [], []

        if overwrite and existing and not dry_run:
            for r in existing:
                if r.tonnage not in seed_map:
                    deleted.append(r.tonnage)
            if deleted:
                session.query(StampingTonnagePrice).filter(
                    StampingTonnagePrice.year == YEAR,
                    StampingTonnagePrice.tonnage.in_([t for t in deleted]),
                ).delete(synchronize_session=False)
                session.commit()
            # overwrite 模式下已有记录也要更新，清空 map 后按插入/更新逻辑重走
            existing = existing_records(session, YEAR)
            existing_map = {r.tonnage: Decimal(str(r.price_per_stroke)) for r in existing}

        for tonnage, price in seed_map.items():
            old_price = existing_map.get(tonnage)
            if old_price is None:
                if not dry_run:
                    session.add(StampingTonnagePrice(
                        year=YEAR, tonnage=tonnage, price_per_stroke=price,
                    ))
                inserted.append((tonnage, float(price)))
            elif old_price != price:
                if dry_run:
                    skipped.append((tonnage, float(old_price), float(price), "would update"))
                elif overwrite:
                    rec = (
                        session.query(StampingTonnagePrice)
                        .filter(
                            StampingTonnagePrice.year == YEAR,
                            StampingTonnagePrice.tonnage == tonnage,
                        )
                        .first()
                    )
                    rec.price_per_stroke = price
                    updated.append((tonnage, float(price)))
                else:
                    skipped.append((tonnage, float(old_price), float(price), "different price, kept"))
            else:
                skipped.append((tonnage, float(old_price), float(price), "same"))

        if not dry_run:
            session.commit()

        mode = "DRY-RUN" if dry_run else "WRITE"
        print(f"[{mode}] year={YEAR} seed_count={len(SEED_2026)} existing={len(existing)}")
        print(f"  inserted   ({len(inserted)}): {inserted}")
        print(f"  updated    ({len(updated)}):  {updated}")
        print(f"  skipped    ({len(skipped)}):  {skipped if len(skipped) <= 8 else skipped[:8] + ['...']}")
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
    args = parser.parse_args()
    run(dry_run=args.dry_run, overwrite=args.overwrite)
