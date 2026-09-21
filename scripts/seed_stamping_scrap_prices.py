"""
种子数据：冲压废料月度销售价格（2025 全年 + 2026 年 1-6 月）

用法（仓库根目录）::

    python -X utf8 -m scripts.seed_stamping_scrap_prices
"""

from __future__ import annotations

from decimal import Decimal

from app.common.audit import SYSTEM_USER, audit_create, audit_update
from app.common.scrap_categories import (
    SCRAP_CATEGORY_ALUMINUM,
    SCRAP_CATEGORY_STEEL,
)
from app.database import DatabaseConfig
from app.models.yishiyiyi import StampingScrapPrice
from app.services.masterdata.location.service import LocationService

STEEL_DEDUCTIONS = {
    "芜湖": Decimal("149.39"),
    "鄂尔多斯": Decimal("391.53"),
    "大连": Decimal("0.00"),
    "青岛": Decimal("0.00"),
    "福州": Decimal("0.00"),
}
ALUMINUM_DEDUCTION = Decimal("94.34")

WH_MARKET_2025 = [
    2438.05,
    2402.65,
    2389.38,
    2324.48,
    2340.71,
    2269.91,
    2301.77,
    2336.28,
    2345.13,
    2345.13,
    2353.98,
    2309.73,
]
DL_MARKET_2025 = [
    2044.25,
    2008.85,
    1995.58,
    1970.5,
    1946.9,
    1876.11,
    1907.96,
    1973.45,
    1975.16,
    1977,
    1982.3,
    1933.34,
]
QD_MARKET_2025 = [
    2106.5,
    2079,
    2054,
    1990,
    1991.5,
    1994,
    2105.67,
    2189,
    2290,
    2190,
    2149,
    2139,
]
LB_MARKET_2025 = [
    15846.37,
    15992.92,
    16491.11,
    16088.1,
    15910.76,
    16265.17,
    16327.43,
    16466.81,
    16546.1,
    16590.27,
    17036.28,
    17294.18,
]
FZ_MARKET_2025 = [2123.89, 2210.44, 2210.44, 2192.25, 2164.96]

WH_MARKET_2026 = [2309.73, 2309.73, 2309.73, 2336.28, 2336.28, 2336.28]
DL_MARKET_2026 = [1933.34, 1933.34, 1933.34, 1957.10, 1957.10, 1957.10]
QD_MARKET_2026 = [2139, 2139, 2139, 2139, 2139, 2139]
FZ_MARKET_2026 = [2123.89, 2123.89, 2123.89, 2138.64, 2138.64, 2138.64]
LB_MARKET_2026 = [17294.18, 17294.18, 17294.18, 19411.42, 19411.42, 19411.42]


def _row(
    location: str,
    year: int,
    month: int,
    market_price: float | Decimal,
    remark: str,
    *,
    scrap_category: str,
) -> dict:
    market = Decimal(str(market_price))
    if scrap_category == SCRAP_CATEGORY_ALUMINUM:
        deduction = ALUMINUM_DEDUCTION
    else:
        deduction = STEEL_DEDUCTIONS[location]
    return {
        "location": location,
        "scrap_category": scrap_category,
        "year": year,
        "month": month,
        "market_price": market,
        "deduction_fee": deduction,
        "net_price": market - deduction,
        "remark": remark,
    }


def _aluminum_rows(
    year: int,
    month: int,
    market_price: float | Decimal,
    remark: str,
    locations: list[str],
) -> list[dict]:
    return [
        _row(
            location,
            year,
            month,
            market_price,
            remark,
            scrap_category=SCRAP_CATEGORY_ALUMINUM,
        )
        for location in locations
    ]


def build_seed_rows(locations: list[str]) -> list[dict]:
    rows: list[dict] = []

    for month_idx in range(12):
        month = month_idx + 1
        remark = "2025年常规价格"
        rows.append(
            _row(
                "芜湖",
                2025,
                month,
                WH_MARKET_2025[month_idx],
                remark,
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )
        rows.append(
            _row(
                "鄂尔多斯",
                2025,
                month,
                WH_MARKET_2025[month_idx],
                remark,
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )
        rows.append(
            _row(
                "大连",
                2025,
                month,
                DL_MARKET_2025[month_idx],
                f"{remark}（无扣费）",
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )
        rows.append(
            _row(
                "青岛",
                2025,
                month,
                QD_MARKET_2025[month_idx],
                f"{remark}（无扣费）",
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )
        rows.extend(_aluminum_rows(2025, month, LB_MARKET_2025[month_idx], remark, locations))

    for idx, month in enumerate([8, 9, 10, 11, 12]):
        rows.append(
            _row(
                "福州",
                2025,
                month,
                FZ_MARKET_2025[idx],
                "2025年8-12月价格（无扣费）",
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )

    for month_idx in range(6):
        month = month_idx + 1
        remark = "2026年1-6月价格"
        rows.append(
            _row(
                "芜湖",
                2026,
                month,
                WH_MARKET_2026[month_idx],
                remark,
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )
        rows.append(
            _row(
                "鄂尔多斯",
                2026,
                month,
                WH_MARKET_2026[month_idx],
                remark,
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )
        rows.append(
            _row(
                "大连",
                2026,
                month,
                DL_MARKET_2026[month_idx],
                f"{remark}（无扣费）",
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )
        rows.append(
            _row(
                "青岛",
                2026,
                month,
                QD_MARKET_2026[month_idx],
                f"{remark}（无扣费）",
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )
        rows.append(
            _row(
                "福州",
                2026,
                month,
                FZ_MARKET_2026[month_idx],
                f"{remark}（无扣费）",
                scrap_category=SCRAP_CATEGORY_STEEL,
            )
        )
        rows.extend(_aluminum_rows(2026, month, LB_MARKET_2026[month_idx], remark, locations))

    return rows


def seed_scrap_prices() -> None:
    DatabaseConfig.create_tables()
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    create_audit = audit_create(SYSTEM_USER)
    update_audit = audit_update(SYSTEM_USER)
    locations = LocationService().list_registered(db)
    if not locations:
        raise RuntimeError("基地主数据为空，无法写入废料价种子")
    rows = build_seed_rows(locations)

    try:
        print(f"准备写入 {len(rows)} 条记录...")
        created = 0
        updated = 0

        for payload in rows:
            existing = (
                db.query(StampingScrapPrice)
                .filter(
                    StampingScrapPrice.location == payload["location"],
                    StampingScrapPrice.scrap_category == payload["scrap_category"],
                    StampingScrapPrice.year == payload["year"],
                    StampingScrapPrice.month == payload["month"],
                )
                .first()
            )
            if existing:
                existing.market_price = payload["market_price"]
                existing.deduction_fee = payload["deduction_fee"]
                existing.net_price = payload["net_price"]
                existing.remark = payload["remark"]
                existing.updated_by = update_audit["updated_by"]
                updated += 1
            else:
                db.add(StampingScrapPrice(**payload, **create_audit))
                created += 1

        db.commit()
        print(f"数据填充完成：新增 {created} 条，更新 {updated} 条。")
    except Exception as exc:
        db.rollback()
        print(f"插入失败，已回滚：{exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_scrap_prices()
