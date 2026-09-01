"""清空冲压零件核价结果后，重算芜湖 T13J 2026-01 钢材联动 + 零件核价。"""

from __future__ import annotations

import logging
from collections import Counter
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER
from app.database import DatabaseConfig
from app.models.costing import (
    StampingPartCost,
    StampingPartCostCalcLog,
    SteelPrice,
    SteelPriceCalcLog,
)
from app.models.stamping import StampingPart
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.services.costing.stamping_part_cost.calc.orchestrator import (
    StampingPartCostCalcOrchestrator,
)
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.steel_price.calc.models import SteelPriceCalcRequest
from app.services.costing.steel_price.calc.orchestrator import SteelPriceCalcOrchestrator

YEAR = 2026
MONTH = 1
LOCATION = "芜湖"
VEHICLE = "T13J"
SAMPLE_PART = "502008024AA"
CANONICAL = {"冷轧", "镀锌", "酸洗"}

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


def _delete_stamping_cost_data(db: Session) -> None:
    cost_n = db.query(StampingPartCost).delete(synchronize_session=False)
    log_n = db.query(StampingPartCostCalcLog).delete(synchronize_session=False)
    steel_n = (
        db.query(SteelPrice)
        .filter(
            SteelPrice.year == YEAR,
            SteelPrice.month == MONTH,
            or_(SteelPrice.location == LOCATION, SteelPrice.location == f"{LOCATION}基地"),
        )
        .delete(synchronize_session=False)
    )
    steel_log_n = (
        db.query(SteelPriceCalcLog)
        .filter(
            SteelPriceCalcLog.year == YEAR,
            SteelPriceCalcLog.month == MONTH,
            or_(
                SteelPriceCalcLog.location == LOCATION,
                SteelPriceCalcLog.location == f"{LOCATION}基地",
            ),
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    print(
        "已删除: "
        f"stamping_part_costs={cost_n}, "
        f"stamping_part_cost_calc_logs={log_n}, "
        f"steel_prices(芜湖 2026-01)={steel_n}, "
        f"steel_price_calc_logs(芜湖 2026-01)={steel_log_n}"
    )


def _suppliers(db: Session) -> list[str]:
    rows = (
        db.query(StampingPart.stamping_supplier)
        .filter(
            StampingPart.location == LOCATION,
            StampingPart.vehicle_model == VEHICLE,
        )
        .distinct()
        .all()
    )
    return sorted({(item[0] or "").strip() for item in rows if (item[0] or "").strip()})


def main() -> int:
    factory = DatabaseConfig.get_session_factory()
    db = factory()
    errors = 0
    try:
        print(f"=== 清空冲压成本并重算 {LOCATION} {VEHICLE} {YEAR}-{MONTH:02d} ===")
        _delete_stamping_cost_data(db)

        print("\n=== Step 钢材联动（按 T13J 全部牌号落库）===")
        steel_result = SteelPriceCalcOrchestrator().calculate(
            db,
            SteelPriceCalcRequest(
                year=YEAR,
                month=MONTH,
                location=LOCATION,
                vehicle_model=VEHICLE,
            ),
            current_user=SYSTEM_USER,
        )
        print(
            f"status={steel_result.status} materials={steel_result.material_count} "
            f"enriched={steel_result.enriched_count} no_base={steel_result.no_base_count} "
            f"created={steel_result.created_count} updated={steel_result.updated_count} "
            f"skipped_approved={steel_result.skipped_approved_count} "
            f"failed={steel_result.failed_count}"
        )
        if steel_result.status == "failed" or steel_result.no_base_count:
            print(steel_result.detail_text[-2000:] if steel_result.detail_text else "")
            errors += 1

        steel_rows = (
            db.query(SteelPrice)
            .filter(
                SteelPrice.year == YEAR,
                SteelPrice.month == MONTH,
                SteelPrice.location == LOCATION,
            )
            .all()
        )
        grades = sorted({(row.grade or "").strip() for row in steel_rows})
        categories = sorted({(row.category_name or "").strip() for row in steel_rows})
        print(f"落库 steel_prices={len(steel_rows)} 大类={categories} 牌号数={len(grades)}")
        print(f"牌号: {', '.join(grades)}")
        if not grades or set(grades) <= CANONICAL:
            print("错误：落库牌号应是工艺牌号，不能只是冷轧/镀锌/酸洗")
            errors += 1
        if CANONICAL & set(grades):
            print(f"警告：落库 grade 含大类名 {CANONICAL & set(grades)}")

        suppliers = _suppliers(db)
        print(f"\n=== Step 零件核价 工厂={suppliers} ===")
        part_orch = StampingPartCostCalcOrchestrator()
        resolver = PriceResolver()
        totals = Counter()
        for supplier in suppliers:
            result = part_orch.calculate(
                db,
                StampingPartCostCalcDTO(
                    year=YEAR,
                    month=MONTH,
                    location=LOCATION,
                    stamping_supplier=supplier,
                    vehicle_model=VEHICLE,
                ),
                current_user=SYSTEM_USER,
            )
            totals["parts"] += result.total_parts
            totals["ok"] += result.success_count
            totals["fail"] += result.failed_count
            print(
                f"  {supplier}: status={result.status} "
                f"total={result.total_parts} ok={result.success_count} "
                f"fail={result.failed_count}"
            )
            reasons: Counter[str] = Counter()
            for item in result.failed_items:
                reasons[item.reason] += 1
            for reason, count in reasons.most_common(8):
                print(f"    - {count}× {reason}")

        persisted = (
            db.query(StampingPartCost)
            .filter(
                StampingPartCost.year == YEAR,
                StampingPartCost.month == MONTH,
                StampingPartCost.location == LOCATION,
                StampingPartCost.vehicle_model == VEHICLE,
            )
            .all()
        )
        print(
            f"\n落库零件核价 {len(persisted)} 行 "
            f"(编排合计 ok={totals['ok']} fail={totals['fail']} / {totals['parts']})"
        )
        if totals["fail"]:
            errors += 1

        sample = (
            db.query(StampingPartCost)
            .filter(
                StampingPartCost.year == YEAR,
                StampingPartCost.month == MONTH,
                StampingPartCost.location == LOCATION,
                StampingPartCost.vehicle_model == VEHICLE,
                StampingPartCost.part_number == SAMPLE_PART,
            )
            .first()
        )
        print(f"\n=== 样件 {SAMPLE_PART} ===")
        if sample is None:
            print("未落库")
            errors += 1
        else:
            print(
                f"status={sample.calc_status} mill={sample.steel_mill} "
                f"ton={sample.steel_ton_price} material={sample.material} "
                f"thick={sample.thickness} unit={sample.unit_cost} "
                f"fail={sample.calc_fail_reason}"
            )
            if sample.material and sample.thickness is not None:
                matched = resolver.find_steel_prices(
                    db,
                    year=YEAR,
                    month=MONTH,
                    location=LOCATION,
                    grade=(sample.material or "").strip(),
                    thickness=Decimal(str(sample.thickness)),
                )
                matched_grades = {(row.grade or "").strip() for row in matched}
                print(f"牌号取价命中 {len(matched)} 条 grade={matched_grades}")
                if matched_grades != {(sample.material or "").strip()}:
                    print("错误：零件核价取价不是严格牌号匹配")
                    errors += 1
            if sample.calc_status != "success":
                errors += 1

        if errors:
            print(f"\n测试未通过，问题数={errors}")
            return 1
        print("\n测试通过")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
