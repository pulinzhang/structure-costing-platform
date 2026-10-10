"""拼焊件导出/列表展示：子片料厚·长·宽·钢材吨价用 / 拼接。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.measures import KG_PER_TON, MM3_G_PER_CM3_TO_KG
from app.common.money import Q2, optional_format_money
from app.common.swing_shear import steel_kg_price_with_swing_shear
from app.models.costing import StampingPartCost, SteelPrice
from app.models.stamping.tailor_weld_blank import StampingTailorWeldBlank
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.part.tailor_weld_blank import (
    StampingTailorWeldBlankRepository,
)
from app.services.costing.stamping_part_cost.export.formatters import formula_number
from app.services.costing.stamping_part_cost.helpers import (
    format_ton_price_label,
    join_slash_formatted,
    join_slash_ton_prices,
)
from app.services.masterdata.location.service import LocationService

SteelPriceKey = tuple[int, int, str, str, Decimal]


@dataclass(slots=True)
class PartCostDisplayFields:
    """核价行展示字段（拼焊件为子片拼接）。"""

    is_tailor_welded: bool
    thickness: str | None
    sheet_length: str | None
    sheet_width: str | None
    steel_ton_price: str | None
    steel_kg_price_display: str | None
    blank_steel_ids: list[int]
    blank_steels: list[SteelPrice]
    blank_terms: list[TailorWeldBlankTerm]


@dataclass(slots=True)
class TailorWeldBlankTerm:
    """拼焊子片：工艺清单按片分行；缺尺寸/单价时对应格留空。"""

    blank_seq: int
    length: Decimal | None
    width: Decimal | None
    thickness: Decimal | None
    parts_per_sheet: int | None
    steel_kg_price: Decimal | None
    steel: SteelPrice | None


def blank_term_has_mass_inputs(term: TailorWeldBlankTerm) -> bool:
    return (
        term.length is not None
        and term.width is not None
        and term.thickness is not None
        and term.parts_per_sheet is not None
        and term.parts_per_sheet > 0
    )


def load_blanks_by_part_id(
    db: Session,
    rows: list[StampingPartCost],
    blank_repo: StampingTailorWeldBlankRepository | None = None,
) -> dict[int, list[StampingTailorWeldBlank]]:
    repo = blank_repo or StampingTailorWeldBlankRepository()
    part_ids = [int(row.source_part_id) for row in rows]
    if not part_ids:
        return {}
    blanks_by_part: dict[int, list[StampingTailorWeldBlank]] = {}
    for blank in repo.list_by_part_ids(db, part_ids):
        blanks_by_part.setdefault(blank.part_id, []).append(blank)
    return blanks_by_part


def build_steel_price_index(
    db: Session,
    rows: list[StampingPartCost],
    steel_repo: SteelPriceRepository | None = None,
) -> dict[SteelPriceKey, SteelPrice]:
    """(year, month, location, grade, thickness) → SteelPrice 行。"""
    repo = steel_repo or SteelPriceRepository()
    index: dict[SteelPriceKey, SteelPrice] = {}
    scopes = {(row.year, row.month, row.location) for row in rows}
    for year, month, location in scopes:
        names = LocationService().expand_for_query(db, location)
        seen_locations: set[str] = set()
        for candidate in names:
            if candidate in seen_locations:
                continue
            seen_locations.add(candidate)
            for record in repo.list_for_export(db, year=year, month=month, location=candidate):
                grade = (record.grade or "").strip()
                if not grade or record.thickness is None:
                    continue
                record_names = LocationService().expand_for_query(db, record.location)
                if not record_names:
                    record_names = [(record.location or "").strip()]
                for loc in record_names:
                    index[(record.year, record.month, loc, grade, record.thickness)] = record
    return index


def lookup_blank_steel(
    row: StampingPartCost,
    blank: StampingTailorWeldBlank,
    price_index: dict[SteelPriceKey, SteelPrice],
) -> SteelPrice | None:
    grade = (blank.material or row.material or "").strip()
    thickness = blank.thickness
    if not grade or thickness is None:
        return None
    loc = row.location.strip()
    if not loc:
        return None
    return price_index.get((row.year, row.month, loc, grade, thickness))


def _join_kg_prices(ton_prices: list[Decimal | None]) -> str | None:
    """子片吨价 → 元/kg 文本，用 / 拼接。"""
    if not ton_prices:
        return None
    labels: list[str] = []
    has_price = False
    for ton in ton_prices:
        if ton is None:
            labels.append("—")
            continue
        has_price = True
        kg = ton / KG_PER_TON
        labels.append(format_ton_price_label(kg))
    if not has_price:
        return None
    return "/".join(labels)


def _blank_parts_per_sheet(row: StampingPartCost, blank: StampingTailorWeldBlank) -> int | None:
    if blank.parts_per_sheet is not None and blank.parts_per_sheet > 0:
        return int(blank.parts_per_sheet)
    parent = row.parts_per_sheet
    if parent is not None and int(parent) > 0:
        return int(parent)
    return None


def build_tailor_blank_terms(
    row: StampingPartCost,
    blanks: list[StampingTailorWeldBlank],
    price_index: dict[SteelPriceKey, SteelPrice],
) -> list[TailorWeldBlankTerm]:
    """按子片序号收集导出行（缺尺寸/单价仍占一行，格留空）。"""
    terms: list[TailorWeldBlankTerm] = []
    for blank in sorted(blanks, key=lambda item: (item.blank_seq or 0, item.id or 0)):
        length = blank.sheet_length
        width = blank.sheet_width
        thickness = blank.thickness
        parts_per_sheet = _blank_parts_per_sheet(row, blank)
        steel = lookup_blank_steel(row, blank, price_index)
        steel_kg = None
        if steel is not None and steel.final_price_per_ton is not None:
            mill_ton = Decimal(str(steel.final_price_per_ton))
            surcharge = row.swing_shear_fee_per_ton
            steel_kg = steel_kg_price_with_swing_shear(mill_ton, surcharge)
        terms.append(
            TailorWeldBlankTerm(
                blank_seq=int(blank.blank_seq or 0),
                length=Decimal(str(length)) if length is not None else None,
                width=Decimal(str(width)) if width is not None else None,
                thickness=Decimal(str(thickness)) if thickness is not None else None,
                parts_per_sheet=parts_per_sheet,
                steel_kg_price=steel_kg,
                steel=steel,
            )
        )
    return terms


def build_blank_row_m_formula(excel_row: int, density: Decimal) -> str:
    """子片行 P：与普通件相同，引用本行 J/M/N/O（料厚/长/宽/可制件数）。"""
    return (
        f"=M{excel_row}*N{excel_row}*J{excel_row}"
        f"*{formula_number(density)}/{formula_number(MM3_G_PER_CM3_TO_KG)}/O{excel_row}"
    )


def build_tailor_group_n_formula(first_row: int, last_row: int) -> str:
    return f"=K{first_row}/SUM(P{first_row}:P{last_row})"


def build_tailor_group_o_formula(first_row: int, last_row: int) -> str:
    return f"=SUM(P{first_row}:P{last_row})-K{first_row}"


def build_tailor_group_r_formula(
    blank_rows: list[int],
    *,
    first_row: int,
    last_row: int,
    loss_rate: Decimal,
    recovery: Decimal,
) -> str:
    """U = Σ(Pi×Si×(1+λ)) − ΣP×λ×η×T − R×η×T，Pi/Si 引用各子片行。"""
    loss = formula_number(loss_rate)
    eta = formula_number(recovery)
    purchase = "+".join(f"P{row}*S{row}*(1+{loss})" for row in blank_rows)
    return (
        f"={purchase}"
        f"-SUM(P{first_row}:P{last_row})*{loss}*{eta}*T{first_row}"
        f"-R{first_row}*T{first_row}*{eta}"
    )


def resolve_part_cost_display(
    row: StampingPartCost,
    blanks: list[StampingTailorWeldBlank],
    price_index: dict[SteelPriceKey, SteelPrice],
) -> PartCostDisplayFields:
    blanks = sorted(blanks, key=lambda item: (item.blank_seq or 0, item.id or 0))
    if len(blanks) >= 2:
        terms = build_tailor_blank_terms(row, blanks, price_index)
        blank_ton_for_display: list[Decimal | None] = []
        blank_steels_display: list[SteelPrice] = []
        blank_ids_display: list[int] = []
        for blank in blanks:
            steel = lookup_blank_steel(row, blank, price_index)
            if steel is not None:
                blank_steels_display.append(steel)
                blank_ids_display.append(steel.id)
                blank_ton_for_display.append(Decimal(str(steel.final_price_per_ton)))
            else:
                blank_ton_for_display.append(None)
        steel_ton_price = join_slash_ton_prices(blank_ton_for_display)
        if steel_ton_price is None and row.steel_ton_price is not None:
            steel_ton_price = format_ton_price_label(Decimal(str(row.steel_ton_price)))
        return PartCostDisplayFields(
            is_tailor_welded=True,
            thickness=join_slash_formatted([blank.thickness for blank in blanks], Q2, 2),
            sheet_length=join_slash_formatted([blank.sheet_length for blank in blanks], Q2, 2),
            sheet_width=join_slash_formatted([blank.sheet_width for blank in blanks], Q2, 2),
            steel_ton_price=steel_ton_price,
            steel_kg_price_display=_join_kg_prices(blank_ton_for_display),
            blank_steel_ids=list(dict.fromkeys(blank_ids_display)),
            blank_steels=blank_steels_display,
            blank_terms=terms,
        )

    steel_ton = row.steel_ton_price
    steel_ton_text = (
        format_ton_price_label(Decimal(str(steel_ton))) if steel_ton is not None else None
    )
    steel_kg_text = None
    if steel_ton is not None:
        steel_kg_text = format_ton_price_label(Decimal(str(steel_ton)) / KG_PER_TON)
    return PartCostDisplayFields(
        is_tailor_welded=False,
        thickness=optional_format_money(row.thickness, Q2, 2),
        sheet_length=optional_format_money(row.sheet_length, Q2, 2),
        sheet_width=optional_format_money(row.sheet_width, Q2, 2),
        steel_ton_price=steel_ton_text,
        steel_kg_price_display=steel_kg_text,
        blank_steel_ids=[row.steel_price_id] if row.steel_price_id is not None else [],
        blank_steels=[],
        blank_terms=[],
    )


def format_multi_steel_trace(
    steels: list[SteelPrice],
    *,
    format_steel_price_excel_trace: Callable[[SteelPrice], str],
) -> str:
    if not steels:
        return ""
    unique: list[SteelPrice] = []
    seen: set[int] = set()
    for steel in steels:
        if steel.id in seen:
            continue
        seen.add(steel.id)
        unique.append(steel)
    if len(unique) == 1:
        return format_steel_price_excel_trace(unique[0])
    lines: list[str] = []
    for steel in unique:
        ton = format_ton_price_label(Decimal(str(steel.final_price_per_ton)))
        grade = (steel.grade or "").strip()
        thick = optional_format_money(steel.thickness, Q2, 2) or ""
        head = f"[{grade}@{thick} {ton}元/吨]"
        body = format_steel_price_excel_trace(steel)
        lines.append(f"{head}\n{body}" if body else head)
    return "\n---\n".join(lines)


def format_steel_ids(ids: list[int]) -> str:
    if not ids:
        return ""
    return "/".join(str(item) for item in ids)
