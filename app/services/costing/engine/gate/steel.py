"""核价引擎门禁：基价与厚度政策覆盖。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate.item import make_item
from app.services.costing.engine.scope.discovery import DiscoveryResult
from app.services.costing.steel_price.calc.coverage import inspect_steel_coverage
from app.services.costing.steel_price.calc.models import SteelPriceCalcRequest


def check_steel_chain(
    db: Session,
    discovery: DiscoveryResult,
) -> list[CostingEngineGateItemVO]:
    location = discovery.location
    year = discovery.year
    month = discovery.month
    request = SteelPriceCalcRequest(year=year, month=month, location=location)
    report = inspect_steel_coverage(db, request)
    if not report.has_materials:
        ok_msg = "无材料规格，跳过钢种覆盖检查"
        return [
            make_item(
                code="base_price",
                ok=True,
                missing=[],
                message=ok_msg,
                location=location,
                year=year,
                month=month,
            ),
            make_item(
                code="thickness_policy",
                ok=True,
                missing=[],
                message=ok_msg,
                location=location,
                year=year,
                month=month,
            ),
        ]

    base_item = make_item(
        code="base_price",
        ok=report.base_ok,
        missing=report.missing_base,
        message=(
            f"基价覆盖完整，展开 {report.row_count} 行"
            if report.base_ok
            else f"基价覆盖不全：{report.no_base_count} 个规格无匹配"
        ),
        location=location,
        year=year,
        month=month,
    )

    if not report.base_ok:
        return [
            base_item,
            make_item(
                code="thickness_policy",
                ok=True,
                missing=["基价未覆盖完整，厚度政策未完整校验"],
                message="基价未齐时跳过厚度硬校验（不阻断；可先补基价与厚度政策）",
                location=location,
                year=year,
                month=month,
                with_navigate=True,
            ),
        ]

    thickness_ok = len(report.thickness_missing) == 0
    return [
        base_item,
        make_item(
            code="thickness_policy",
            ok=thickness_ok,
            missing=report.thickness_missing,
            message=(
                "厚度加减价政策可匹配"
                if thickness_ok
                else (f"厚度政策匹配失败 {len(report.thickness_missing)} 项" "，须补齐后再启动")
            ),
            location=location,
            year=year,
            month=month,
            with_navigate=not thickness_ok,
        ),
    ]
