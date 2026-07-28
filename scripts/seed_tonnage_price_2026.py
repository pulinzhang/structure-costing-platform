"""
种子数据脚本：把 2026 年冲压吨位价格写入数据库
- 默认幂等（已存在 (year, tonnage) 跳过）
- --overwrite 时先删后插
- --dry-run 只打印，不写入
"""
import argparse
import sys
from pathlib import Path

# 允许在仓库根目录直接运行：把仓库根加入 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models import StampingTonnagePrice


# 2026 年真实数据（年度 + 吨位 联合唯一）
# 注意：400T=0.74 之后 500T=0.73，价格反向回落，已知疑点，待业务侧确认
SEED_2026 = [
    (40, 0.05),
    (60, 0.05),
    (63, 0.05),
    (80, 0.07),
    (100, 0.09),
    (110, 0.13),
    (125, 0.13),
    (160, 0.13),
    (200, 0.19),
    (250, 0.25),
    (315, 0.36),
    (400, 0.74),
    (500, 0.73),
    (630, 0.75),
    (800, 1.38),
    (1000, 1.61),
    (1200, 1.85),
    (1250, 1.85),
    (1300, 2.36),
    (1500, 2.93),
    (1600, 3.15),
    (2000, 3.40),
    (2400, 4.08),
]

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
        existing_map = {r.tonnage: r.price_per_stroke for r in existing}

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
            existing_map = {}

        for tonnage, price in seed_map.items():
            old_price = existing_map.get(tonnage)
            if old_price is None:
                if dry_run:
                    inserted.append((tonnage, price))
                else:
                    session.add(StampingTonnagePrice(
                        year=YEAR, tonnage=tonnage, price_per_stroke=price,
                    ))
                    inserted.append((tonnage, price))
            elif old_price != price:
                if dry_run:
                    skipped.append((tonnage, old_price, price, "would update"))
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
                    updated.append((tonnage, price))
                else:
                    skipped.append((tonnage, old_price, price, "different price, kept"))
            else:
                skipped.append((tonnage, old_price, price, "same"))

        if not dry_run:
            session.commit()

        mode = "DRY-RUN" if dry_run else "WRITE"
        print(f"[{mode}] year={YEAR} seed_count={len(SEED_2026)} existing={len(existing)}")
        print(f"  inserted   ({len(inserted)}): {inserted[:5]}{'...' if len(inserted) > 5 else ''}")
        print(f"  updated    ({len(updated)}):  {updated}")
        print(f"  skipped    ({len(skipped)}):  {skipped if len(skipped) <= 6 else skipped[:6] + ['...']}")
        print(f"  deleted    ({len(deleted)}):  {deleted}")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run, overwrite=args.overwrite)
