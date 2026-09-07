"""芜湖 T13J 2026-01：基价表牌号匹配 + 大类厚度政策（现网主库）。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session, selectinload

from app.models.stamping import StampingPart, StampingTailorWeldBlank
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.steel_price.calc.models import (
    CalcRow,
    MaterialThicknessRow,
    SteelPriceCalcRequest,
)
from app.services.costing.steel_price.calc.steps.apply_adjustments import AdjustmentApplier
from app.services.costing.steel_price.calc.steps.enrich_base_price import BasePriceEnricher
from app.services.costing.steel_price.calc.steps.load_materials import MaterialThicknessLoader
from app.services.yishiyiyi.steel_grade_category import SteelGradeCategoryService

YEAR = 2026
MONTH = 1
LOCATION = "芜湖"
VEHICLE_MODEL = "T13J"
VERSION = "V3"
PART_NUMBER = "502008024AA"


def _request() -> SteelPriceCalcRequest:
    return SteelPriceCalcRequest(
        year=YEAR,
        month=MONTH,
        location=LOCATION,
    )


def _t13j_process_spec_rows(db: Session) -> list[dict[str, object]]:
    """T13J 工艺规格（含拼焊子片）；仅用于对照断言，不参与钢价取数。"""
    part_rows = (
        db.query(StampingPart.location, StampingPart.material, StampingPart.thickness)
        .filter(
            StampingPart.location == LOCATION,
            StampingPart.vehicle_model == VEHICLE_MODEL,
            StampingPart.material.isnot(None),
            StampingPart.material != "",
            StampingPart.thickness.isnot(None),
        )
        .all()
    )
    blank_rows = (
        db.query(
            StampingPart.location,
            StampingTailorWeldBlank.material,
            StampingTailorWeldBlank.thickness,
        )
        .join(
            StampingTailorWeldBlank,
            StampingTailorWeldBlank.part_id == StampingPart.id,
        )
        .filter(
            StampingPart.location == LOCATION,
            StampingPart.vehicle_model == VEHICLE_MODEL,
            StampingTailorWeldBlank.material.isnot(None),
            StampingTailorWeldBlank.material != "",
            StampingTailorWeldBlank.thickness.isnot(None),
        )
        .all()
    )
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict[str, object]] = []
    for loc, material, thickness in list(part_rows) + list(blank_rows):
        location = (loc or "").strip()
        grade = (material or "").strip()
        if not location or not grade or thickness is None:
            continue
        key = (location, grade, str(thickness))
        if key in seen:
            continue
        seen.add(key)
        rows.append({"location": location, "material": grade, "thickness": thickness})
    return rows


def _ton(row: CalcRow) -> Decimal:
    return row.to_persist_payload(
        calc_batch_id="t13j-2026-01", formula_version="test"
    ).final_price_per_ton


def _calc_rows(db: Session) -> list[CalcRow]:
    request = _request()
    loaded = MaterialThicknessLoader().load(db, request)
    rows, _no_base_count, _details = BasePriceEnricher().enrich(db, request, loaded)
    applier = AdjustmentApplier()
    policies = applier.load_policies(db, request)
    if not policies:
        pytest.skip(f"无加减价政策: {YEAR}-{MONTH:02d}")
    rows = applier.apply_thickness(db, rows, policies)
    return applier.apply_width(rows, policies)


@pytest.mark.integration
def test_t13j_process_grades_map_to_cold_or_galv(db_session: Session) -> None:
    raw = _t13j_process_spec_rows(db_session)
    if not raw:
        pytest.skip(f"无工艺规格: {LOCATION}/{VEHICLE_MODEL}")
    grades = sorted({str(row.get("material") or "").strip() for row in raw})
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
        pytest.skip(f"无材料行: {LOCATION}")
    t13j = _t13j_process_spec_rows(db_session)
    t13j_keys = {(str(row["material"]).strip(), Decimal(str(row["thickness"]))) for row in t13j}
    loaded_keys = {(row.material, row.thickness) for row in loaded}
    assert t13j_keys <= loaded_keys
    assert len(t13j_keys) == 34
    assert "DC01" in {row.material for row in loaded}
    assert "DC03" in {row.material for row in loaded}
    assert "DC51D+Z" in {row.material for row in loaded}
    assert "冷轧" not in {row.material for row in loaded}


@pytest.mark.integration
def test_t13j_grades_missing_from_base_table_do_not_borrow_category_price(
    db_session: Session,
) -> None:
    """基价表没有的牌号不按冷轧大类回退；DCO3/DCO4 与 DC03/DC04 视为同一牌号。"""
    request = SteelPriceCalcRequest(year=YEAR, month=MONTH, location=LOCATION)
    dc03_rows, dc03_no_base, dc03_details = BasePriceEnricher().enrich(
        db_session,
        request,
        [MaterialThicknessRow(location=LOCATION, material="DC03", thickness=Decimal("1.2000"))],
    )
    assert dc03_no_base == 0, dc03_details
    assert dc03_rows
    assert {row.grade for row in dc03_rows} == {"DC03"}
    assert {(row.steel_mill or "").strip() for row in dc03_rows} == {"邯钢"}
    assert all(row.base_price == Decimal("3721.00") for row in dc03_rows)

    dc04_rows, dc04_no_base, dc04_details = BasePriceEnricher().enrich(
        db_session,
        request,
        [MaterialThicknessRow(location=LOCATION, material="DC04", thickness=Decimal("0.6500"))],
    )
    assert dc04_no_base == 0, dc04_details
    assert dc04_rows
    assert {row.grade for row in dc04_rows} == {"DC04"}
    assert {(row.steel_mill or "").strip() for row in dc04_rows} == {"马钢"}
    assert all(row.base_price == Decimal("3828.00") for row in dc04_rows)

    category_rows, category_no_base, category_details = BasePriceEnricher().enrich(
        db_session,
        request,
        [MaterialThicknessRow(location=LOCATION, material="冷轧", thickness=Decimal("1.2000"))],
    )
    assert category_rows == []
    assert category_no_base >= 1, f"冷轧@1.2000 应无基价: {category_details}"


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
    t13j_grades = {str(row["material"]).strip() for row in _t13j_process_spec_rows(db_session)}
    t13j_rows = [row for row in rows if row.grade in t13j_grades]
    assert {row.grade for row in t13j_rows} <= {item.material for item in loaded}
    assert {row.category_name for row in t13j_rows} <= {"冷轧", "镀锌"}
    assert all(row.grade != row.category_name for row in t13j_rows)
    assert "DC01" in {row.grade for row in rows}
    assert "HC180Y" in {row.grade for row in rows}
    assert "DC03" in {row.grade for row in rows}
    assert "DC04" in {row.grade for row in rows}

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
    dc01_07 = [row for row in magang_07 if row.grade == "DC01"]
    assert dc01_07
    assert dc01_07[0].base_price == Decimal("3742.00")
    assert dc01_07[0].thickness_adjustment == Decimal("160")
    assert dc01_07[0].processing_fee == Decimal("120.00")
    assert _ton(dc01_07[0]) == Decimal("4022.00")
    hc180y_07 = [row for row in magang_07 if row.grade == "HC180Y"]
    assert hc180y_07
    assert hc180y_07[0].base_price == Decimal("3919.00")
    assert _ton(hc180y_07[0]) == Decimal("4199.00")

    magang_06 = [
        row
        for row in rows
        if (row.steel_mill or "").strip() == "马钢"
        and row.category_name == "冷轧"
        and Decimal(str(row.thickness)) == Decimal("0.6000")
    ]
    assert magang_06
    dc01_06 = [row for row in magang_06 if row.grade == "DC01"]
    assert dc01_06
    assert dc01_06[0].thickness_adjustment == Decimal("200")
    assert _ton(dc01_06[0]) == Decimal("4062.00")
    hc180y_06 = [row for row in magang_06 if row.grade == "HC180Y"]
    assert hc180y_06
    assert hc180y_06[0].base_price == Decimal("3919.00")
    assert _ton(hc180y_06[0]) == Decimal("4239.00")


@pytest.mark.integration
def test_t13j_galvanized_07_picks_lowest_vama(db_session: Session) -> None:
    rows = _calc_rows(db_session)
    galv = [
        row
        for row in rows
        if row.category_name == "镀锌"
        and row.grade == "DC51D+Z"
        and Decimal(str(row.thickness)) == Decimal("0.7000")
    ]
    by_mill = {(row.steel_mill or "").strip(): _ton(row) for row in galv}
    assert set(by_mill) == {"VAMA"}
    assert by_mill["VAMA"] == Decimal("4269.00")
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
