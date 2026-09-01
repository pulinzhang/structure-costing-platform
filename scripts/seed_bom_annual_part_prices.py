"""
种子数据：BOM 年度零件价（青岛 / 2025）

用法（仓库根目录）::

    python -X utf8 -m scripts.seed_bom_annual_part_prices
"""

from __future__ import annotations

from decimal import Decimal

from app.common.audit import SYSTEM_USER, audit_create, audit_update
from app.common.money import Q4, quantize_money
from app.database import DatabaseConfig
from app.models.bom import BomAnnualPartPrice

SEED_LOCATION = "青岛"
SEED_YEAR = 2025

SEED_ROWS: list[tuple[str, str, str, Decimal, str]] = [
    ("QR36410", "焊接方螺母", "pcs", Decimal("0.1750"), "标准件"),
    ("N0111931", "焊接方螺母", "pcs", Decimal("0.0420"), "标准件"),
    ("Q1980616", "承面凸焊螺栓", "pcs", Decimal("0.0500"), "标准件"),
    ("504000341AA", "左D柱下结构增强胶块", "pcs", Decimal("31.4900"), "胶块"),
    ("504000342AA", "右D柱下结构增强胶块", "pcs", Decimal("31.4900"), "胶块"),
    ("M14-4102311", "结构胶", "pcs", Decimal("0.0000"), "胶块"),
]


def seed_annual_part_prices() -> None:
    DatabaseConfig.create_tables()
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    create_audit = audit_create(SYSTEM_USER)
    update_audit = audit_update(SYSTEM_USER)

    try:
        print(f"准备写入 {len(SEED_ROWS)} 条记录" f"（{SEED_LOCATION} / {SEED_YEAR}）...")
        created = 0
        updated = 0
        skipped_approved = 0

        for part_number, part_name, unit, unit_price, supply_type in SEED_ROWS:
            price = quantize_money(unit_price, Q4)
            existing = (
                db.query(BomAnnualPartPrice)
                .filter(
                    BomAnnualPartPrice.location == SEED_LOCATION,
                    BomAnnualPartPrice.year == SEED_YEAR,
                    BomAnnualPartPrice.part_number == part_number,
                )
                .first()
            )
            if existing:
                if existing.audit_status == "approved":
                    skipped_approved += 1
                    continue
                existing.part_name = part_name
                existing.unit = unit
                existing.unit_price = price
                existing.supply_type = supply_type
                existing.updated_by = update_audit["updated_by"]
                updated += 1
            else:
                db.add(
                    BomAnnualPartPrice(
                        location=SEED_LOCATION,
                        year=SEED_YEAR,
                        part_number=part_number,
                        part_name=part_name,
                        unit=unit,
                        unit_price=price,
                        supply_type=supply_type,
                        supplier_name=None,
                        remark=None,
                        audit_status="pending",
                        **create_audit,
                    )
                )
                created += 1

        db.commit()
        message = f"数据填充完成：新增 {created} 条，更新 {updated} 条"
        if skipped_approved:
            message += f"，跳过已审核 {skipped_approved} 条"
        print(f"{message}。")
    except Exception as exc:
        db.rollback()
        print(f"插入失败，已回滚：{exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_annual_part_prices()
