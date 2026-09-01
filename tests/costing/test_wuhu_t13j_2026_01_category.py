"""芜湖 T13J 2026-01：钢厂 + 大类匹配的详细集成测试（现网主库）。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session, selectinload

from app.models.stamping import StampingPart
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.steel_price.calc.models import (
    CalcRow,
    MaterialThicknessRow,
    SteelPriceCalcRequest,
)
from app.services.costing.steel_price.calc.steps.apply_adjustments import AdjustmentApplier
from app.services.costing.steel_price.calc.steps.enrich_base_price import BasePriceEnricher
from app.services.costing.steel_price.calc.steps.load_materials import MaterialThicknessLoader
from app.services.stamping.stamping_service import StampingPartService
from app.services.yishiyiyi.steel_grade_category import SteelGradeCategoryService

YEAR = 2026
MONTH = 1
LOCATION = "芜湖"
VEHICLE_MODEL = "T13J"
VERSION = "V3"
PART_NUMBER = "502008024AA"

COLD_MILLS = {"唐钢", "宝钢", "邯钢", "首钢", "马钢"}
GALV_MILLS = {"VAMA", "唐钢", "宝钢", "邯钢", "首钢", "马钢"}
COLD_THICKNESSES = {
    Decimal("0.6000"),
    Decimal("0.6500"),
    Decimal("0.7000"),
    Decimal("0.8000"),
    Decimal("1.0000"),
    Decimal("1.2000"),
    Decimal("1.4000"),
    Decimal("1.5000"),
    Decimal("1.8000"),
    Decimal("2.0000"),
    Decimal("2.5000"),
}
GALV_THICKNESSES = {
    Decimal("0.6000"),
    Decimal("0.6500"),
    Decimal("0.7000"),
    Decimal("0.8000"),
    Decimal("1.0000"),
    Decimal("1.2000"),
    Decimal("1.5000"),
    Decimal("1.8000"),
}


def _request() -> SteelPriceCalcRequest:
    return SteelPriceCalcRequest(
        year=YEAR,
        month=MONTH,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
    )


def _ton(row: CalcRow) -> Decimal:
    return row.to_persist_payload(
        calc_batch_id="t13j-2026-01", formula_version="test"
    ).final_price_per_ton


def _calc_rows(db: Session) -> list[CalcRow]:
    request = _request()
    loaded = MaterialThicknessLoader().load(db, request)
    rows, no_base_count, details = BasePriceEnricher().enrich(db, request, loaded)
    if no_base_count:
        pytest.fail(f"T13J 大类基价缺口 {no_base_count}: {details}")
    applier = AdjustmentApplier()
    policies = applier.load_policies(db, request)
    if not policies:
        pytest.skip(f"无加减价政策: {YEAR}-{MONTH:02d}")
    rows = applier.apply_thickness(db, rows, policies)
    return applier.apply_width(rows, policies)


@pytest.mark.integration
def test_t13j_process_grades_map_to_cold_or_galv(db_session: Session) -> None:
    raw = StampingPartService().list_material_specs(
        db_session, location=LOCATION, vehicle_model=VEHICLE_MODEL
    )
    if not raw:
        pytest.skip(f"无工艺规格: {LOCATION}/{VEHICLE_MODEL}")
    grades = sorted({(row.get("material") or "").strip() for row in raw})
    category_map = SteelGradeCategoryService().map_grades(db_session, grades)
    missing = [grade for grade in grades if category_map.get(grade) is None]
    assert not missing, f"牌号未进档案: {missing}"
    by_category: dict[str, list[str]] = defaultdict(list)
    for grade in grades:
        name = (category_map[grade].category_name or "").strip()
        by_category[name].append(grade)
    assert set(by_category) == {"冷轧", "镀锌"}
    assert by_category["冷轧"] == [
        "DC01",
        "DC03",
        "DC04",
        "HC180Y",
        "HC260Y",
        "HC340/590DP",
        "HC340LA",
        "HC420/780DP",
        "HC600/980QP",
    ]
    assert by_category["镀锌"] == [
        "DC51D+Z",
        "DC54D+Z",
        "DC56D+Z",
        "HC180YD+Z",
        "HC340/590DPD+Z",
        "HC420/780DPD+Z",
    ]
    assert len(raw) == 34
    assert len(grades) == 15


@pytest.mark.integration
def test_t13j_loader_keeps_every_grade_thickness(db_session: Session) -> None:
    loaded = MaterialThicknessLoader().load(db_session, _request())
    if not loaded:
        pytest.skip(f"无材料行: {LOCATION}/{VEHICLE_MODEL}")
    keys = {(row.material, row.thickness) for row in loaded}
    assert len(keys) == 34
    assert len(loaded) == 34
    assert "DC01" in {row.material for row in loaded}
    assert "DC03" in {row.material for row in loaded}
    assert "DC51D+Z" in {row.material for row in loaded}
    assert "冷轧" not in {row.material for row in loaded}


@pytest.mark.integration
def test_t13j_former_unmatched_grades_share_cold_rolled_base(db_session: Session) -> None:
    """原先按牌号报无匹配的 DC03@1.2 / DC04@0.65 / DC04@1.0，现与冷轧同厂同价。"""
    request = SteelPriceCalcRequest(year=YEAR, month=MONTH, location=LOCATION)
    probes = [
        ("DC03", Decimal("1.2000")),
        ("DC04", Decimal("0.6500")),
        ("DC04", Decimal("1.0000")),
        ("冷轧", Decimal("1.2000")),
        ("冷轧", Decimal("0.6500")),
        ("冷轧", Decimal("1.0000")),
    ]
    by_key: dict[tuple[str, Decimal], list[CalcRow]] = {}
    for grade, thickness in probes:
        rows, no_base, details = BasePriceEnricher().enrich(
            db_session,
            request,
            [MaterialThicknessRow(location=LOCATION, material=grade, thickness=thickness)],
        )
        assert no_base == 0, f"{grade}@{thickness} {details}"
        mills = {(row.steel_mill or "").strip() for row in rows}
        assert mills == COLD_MILLS
        by_key[(grade, thickness)] = rows

    for thickness in (Decimal("1.2000"), Decimal("0.6500"), Decimal("1.0000")):
        grade_key = "DC03" if thickness == Decimal("1.2000") else "DC04"
        left = {
            ((row.steel_mill or "").strip(), row.base_price)
            for row in by_key[(grade_key, thickness)]
        }
        right = {
            ((row.steel_mill or "").strip(), row.base_price) for row in by_key[("冷轧", thickness)]
        }
        assert left == right


@pytest.mark.integration
def test_t13j_calc_rows_persist_each_grade_with_mill_category_price(db_session: Session) -> None:
    loaded = MaterialThicknessLoader().load(db_session, _request())
    rows = _calc_rows(db_session)
    persist_keys = {
        (
            (row.steel_mill or "").strip(),
            row.category_name,
            row.grade,
            row.thickness,
            row.width,
        )
        for row in rows
    }
    assert len(persist_keys) == len(rows)
    assert {row.grade for row in rows} == {item.material for item in loaded}
    assert {row.category_name for row in rows} == {"冷轧", "镀锌"}
    assert all(row.grade != row.category_name for row in rows)

    mills_by_spec: dict[tuple[str, Decimal], set[str]] = defaultdict(set)
    for row in rows:
        mills_by_spec[(row.category_name or "", Decimal(str(row.thickness)))].add(
            (row.steel_mill or "").strip()
        )
    for thickness in COLD_THICKNESSES:
        assert mills_by_spec[("冷轧", thickness)] == COLD_MILLS
    for thickness in GALV_THICKNESSES:
        assert mills_by_spec[("镀锌", thickness)] == GALV_MILLS

    magang_07 = [
        row
        for row in rows
        if (row.steel_mill or "").strip() == "马钢"
        and row.category_name == "冷轧"
        and Decimal(str(row.thickness)) == Decimal("0.7000")
    ]
    assert magang_07
    assert {row.grade for row in magang_07} <= {item.material for item in loaded}
    assert len({row.grade for row in magang_07}) == len(magang_07)
    for row in magang_07:
        assert row.base_price == Decimal("3742.00")
        assert row.thickness_adjustment == Decimal("160")
        assert row.processing_fee == Decimal("120.00")
        assert _ton(row) == Decimal("4022.00")

    magang_06 = [
        row
        for row in rows
        if (row.steel_mill or "").strip() == "马钢"
        and row.category_name == "冷轧"
        and Decimal(str(row.thickness)) == Decimal("0.6000")
    ]
    assert magang_06
    for row in magang_06:
        assert row.thickness_adjustment == Decimal("200")
        assert _ton(row) == Decimal("4062.00")


@pytest.mark.integration
def test_t13j_galvanized_07_picks_lowest_vama(db_session: Session) -> None:
    rows = _calc_rows(db_session)
    galv = [
        row
        for row in rows
        if row.category_name == "镀锌" and Decimal(str(row.thickness)) == Decimal("0.7000")
    ]
    by_mill = {(row.steel_mill or "").strip(): _ton(row) for row in galv}
    assert by_mill["VAMA"] == Decimal("4269.00")
    assert by_mill["马钢"] == Decimal("4832.00")
    wrapped = [
        SimpleNamespace(
            id=index,
            steel_mill=row.steel_mill,
            final_price_per_ton=_ton(row),
        )
        for index, row in enumerate(galv, start=1)
    ]
    picked = PriceResolver().pick_steel_price(wrapped)  # type: ignore[arg-type]
    assert picked is not None
    assert (picked.steel_mill or "").strip() == "VAMA"
    assert Decimal(str(picked.final_price_per_ton)) == Decimal("4269.00")


@pytest.mark.integration
def test_t13j_part_502008024aa_lookup_by_grade(db_session: Session) -> None:
    part = (
        db_session.query(StampingPart)
        .options(selectinload(StampingPart.processes))
        .filter(
            StampingPart.location == LOCATION,
            StampingPart.vehicle_model == VEHICLE_MODEL,
            StampingPart.version == VERSION,
            StampingPart.part_number == PART_NUMBER,
        )
        .one_or_none()
    )
    if part is None:
        pytest.skip(f"无零件: {LOCATION}/{VEHICLE_MODEL}/{VERSION}/{PART_NUMBER}")
    assert (part.material or "").strip() == "DC51D+Z"
    assert Decimal(str(part.thickness)) == Decimal("0.7000")

    found = PriceResolver().find_steel_prices(
        db_session,
        year=YEAR,
        month=MONTH,
        location=LOCATION,
        grade="DC51D+Z",
        thickness=Decimal("0.7000"),
    )
    if not found:
        pytest.skip("芜湖 2026-01 尚未落库钢材联动价")
    categories = {(row.category_name or "").strip() for row in found}
    grades = {(row.grade or "").strip() for row in found}
    assert categories == {"镀锌"}
    assert grades == {"DC51D+Z"}
    picked = PriceResolver().pick_steel_price(found)
    assert picked is not None
    assert (picked.steel_mill or "").strip() == "VAMA"
    assert Decimal(str(picked.final_price_per_ton)) == Decimal("4269.0000")
