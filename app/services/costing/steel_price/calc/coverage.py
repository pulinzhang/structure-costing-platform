"""钢价覆盖：基价展开与厚度适用缺口（引擎门禁与钢价计算共用）。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.money import Q4, format_money
from app.exceptions.base import BusinessException
from app.services.costing.steel_price.calc.models import CalcRow, SteelPriceCalcRequest
from app.services.costing.steel_price.calc.steps.apply_adjustments import AdjustmentApplier
from app.services.costing.steel_price.calc.steps.enrich_base_price import BasePriceEnricher
from app.services.costing.steel_price.calc.steps.load_materials import MaterialThicknessLoader


@dataclass(frozen=True, slots=True)
class SteelCoverageReport:
    row_count: int
    no_base_count: int
    missing_base: list[str]
    base_ok: bool
    thickness_missing: list[str]
    has_materials: bool


def thickness_gap_labels(rows: list[CalcRow]) -> list[str]:
    labels: list[str] = []
    for row in rows:
        if row.thickness_policy_id is None and row.thickness_applicable:
            labels.append(f"{row.grade}@{format_money(row.thickness, Q4, 4)}/{row.steel_mill}")
    return list(dict.fromkeys(labels))[:20]


def raise_if_thickness_gaps(rows: list[CalcRow]) -> None:
    _raise_thickness_missing(thickness_gap_labels(rows))


def assert_steel_calc_thickness(db: Session, request: SteelPriceCalcRequest) -> None:
    report = inspect_steel_coverage(db, request)
    _raise_thickness_missing(report.thickness_missing)


def inspect_steel_coverage(
    db: Session,
    request: SteelPriceCalcRequest,
) -> SteelCoverageReport:
    materials = MaterialThicknessLoader().load(db, request)
    if not materials:
        return SteelCoverageReport(
            row_count=0,
            no_base_count=0,
            missing_base=[],
            base_ok=True,
            thickness_missing=[],
            has_materials=False,
        )

    rows, no_base_count, no_base_details = BasePriceEnricher().enrich(db, request, materials)
    missing_base = no_base_details[:20]
    base_ok = no_base_count == 0 and len(rows) > 0
    if no_base_count == 0 and len(rows) == 0:
        base_ok = False
        missing_base = ["材料有规格但未展开任何基价行"]

    thickness_missing: list[str] = []
    if rows:
        applier = AdjustmentApplier()
        policies = applier.load_policies(db, request)
        rows = applier.apply_thickness(db, rows, policies)
        thickness_missing = thickness_gap_labels(rows)

    return SteelCoverageReport(
        row_count=len(rows),
        no_base_count=no_base_count,
        missing_base=missing_base,
        base_ok=base_ok,
        thickness_missing=thickness_missing,
        has_materials=True,
    )


def _raise_thickness_missing(missing: list[str]) -> None:
    if not missing:
        return
    raise BusinessException(f"厚度政策匹配失败 {len(missing)} 项，须补齐后再计算：{missing[0]}")
