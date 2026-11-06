"""采购对象成本还原：取价、分页粒度、合计行、导出数字。"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

from openpyxl import load_workbook

from app.services.costing.cost_restore.procurement_object.export import (
    export_filename,
    write_workbook,
)
from app.services.costing.cost_restore.procurement_object.rows import (
    MISMATCH,
    NO_CARD,
    NO_WELD_RECORD,
    OTHER_FEE_NOTE,
    ObjectHit,
    RestoreBundle,
    build_object_lines,
    pick_part_cost,
    slice_objects,
)


def _hit(**kwargs: object) -> ObjectHit:
    payload = dict(
        object_id=1,
        supplier_name="芜湖容大",
        vehicle_model="J52",
        object_kind_label="冲压件",
        internal_number="ACA1",
        part_number="P-1",
        part_name="零件",
        vehicle_qty=Decimal("2"),
        level=1,
        source_node_id=10,
    )
    payload.update(kwargs)
    return ObjectHit(**payload)


def _cost(**kwargs: object) -> SimpleNamespace:
    payload = dict(
        id=7,
        part_number="P-1",
        stamping_supplier="甲厂",
        unit_cost=Decimal("10"),
        is_offal_nested=False,
        has_swing_shear=False,
        swing_shear_fee_per_ton=Decimal("0"),
        steel_ton_price=Decimal("5000"),
        scrap_ton_price=Decimal("1000"),
        sheet_length=Decimal("100"),
        sheet_width=Decimal("50"),
        thickness=Decimal("1"),
        parts_per_sheet=2,
        blank_weight_kg=Decimal("1"),
        material="DC01",
        finished_total_kg=Decimal("0.8"),
        material_utilization_pct=Decimal("80"),
        scrap_weight_kg=Decimal("0.2"),
        material_amount_sheet=Decimal("4"),
        loss_scrap_deduction=Decimal("0"),
        process_scrap_deduction=Decimal("0"),
        material_net_per_part=Decimal("4"),
        process_fee_id=None,
        process_fee_amount=Decimal("3"),
        die_fee_id=None,
        die_fee_amount=Decimal("1"),
        gauge_fee_id=None,
        gauge_fee_amount=Decimal("1"),
        finished_finance_fee=Decimal("0.25"),
        finished_management_fee=Decimal("0.25"),
        finished_warehouse_packaging_fee=Decimal("0.25"),
        finished_pretax_profit_fee=Decimal("0.25"),
        steel_price_id=1,
        scrap_price_id=2,
        excel_filename="a.xlsx",
        excel_row=4,
        source_part_id=3,
        automation="单干",
    )
    payload.update(kwargs)
    return SimpleNamespace(**payload)


def _card(**kwargs: object) -> SimpleNamespace:
    item = kwargs.pop("item", None)
    payload = dict(
        total_amount=Decimal("20"),
        stamping_amount=Decimal("20"),
        purchased_amount=Decimal("0"),
        bundle_amount=Decimal("0"),
        material_amount=Decimal("20"),
        welding_amount=Decimal("0"),
        welding_other_fee=Decimal("0"),
        welding_fee_id=None,
        calc_status="success",
        calc_message=None,
        items=[
            item
            or SimpleNamespace(
                sort_no=1,
                cost_source="stamping",
                part_number="P-1",
                match_hint=None,
                unit_price=Decimal("10"),
                effective_qty=Decimal("2"),
                line_amount=Decimal("20"),
            )
        ],
    )
    payload.update(kwargs)
    return SimpleNamespace(**payload)


def _bundle(costs: list | None = None) -> RestoreBundle:
    grouped: dict[tuple[str, str], list] = {}
    for cost in costs or []:
        grouped.setdefault(("J52", cost.part_number), []).append(cost)
    return RestoreBundle(
        part_costs=grouped,
        process_fees={},
        die_fees={},
        die_processes={},
        welding_fees={},
        blanks_by_part_id={},
    )


def test_pick_keeps_one_row_when_unit_cost_matches() -> None:
    chosen, note = pick_part_cost(
        [_cost(id=1, stamping_supplier="甲"), _cost(id=2, stamping_supplier="乙")],
        Decimal("10"),
    )
    assert chosen is not None and chosen.id == 1
    assert note is None


def test_pick_blanks_material_when_factory_prices_differ() -> None:
    chosen, note = pick_part_cost(
        [
            _cost(unit_cost=Decimal("10")),
            _cost(id=8, unit_cost=Decimal("12"), stamping_supplier="乙"),
        ],
        Decimal("9"),
    )
    assert chosen is None
    assert note is not None and "各工厂单价" in note


def test_slice_counts_objects_not_rows() -> None:
    objects = ["a", "b", "c"]
    assert slice_objects(objects, page=2, size=1) == ["b"]


def test_object_without_card_keeps_identity() -> None:
    lines = build_object_lines(_hit(), None, _bundle())
    assert [line.row_type for line in lines] == ["合计"]
    assert lines[0].remark == NO_CARD
    assert lines[0].object_part_number == "P-1"
    assert lines[0].settlement_price is None


def test_stamping_leaf_ties_to_line_amount_and_keeps_total_last() -> None:
    lines = build_object_lines(_hit(), _card(), _bundle([_cost()]))
    assert [line.row_type for line in lines] == ["材料", "叶子小计", "焊接", "合计"]
    material = lines[0]
    assert material.material_net == Decimal("4")
    assert material.material_amount_sheet == Decimal("4")
    assert lines[1].line_amount == Decimal("20")
    assert lines[1].remark is None
    assert lines[2].remark == NO_WELD_RECORD
    assert lines[-1].row_type == "合计"
    assert lines[-1].line_amount == Decimal("20")


def test_offal_does_not_apply_ordinary_material_formula() -> None:
    cost = _cost(is_offal_nested=True, material_amount_sheet=Decimal("99"))
    lines = build_object_lines(_hit(), _card(), _bundle([cost]))
    assert lines[0].material_amount_sheet is None
    assert lines[0].material_net == Decimal("4")
    assert lines[0].remark is None


def test_material_formula_mismatch_is_marked() -> None:
    cost = _cost(material_net_per_part=Decimal("9"))
    lines = build_object_lines(_hit(), _card(), _bundle([cost]))
    assert lines[0].remark == MISMATCH


def test_weld_splits_ecoat_and_notes_other_fee() -> None:
    fee = SimpleNamespace(
        id=4,
        level=1,
        total_welding_fee=Decimal("5"),
        other_fee=Decimal("1"),
        final_welding_fee=Decimal("6"),
        items=[
            SimpleNamespace(
                id=1,
                line_no=1,
                standard_process_name="焊点",
                process_token=None,
                process_qty=Decimal("2"),
                unit_price=Decimal("1"),
                line_fee=Decimal("2"),
                match_status="matched",
            ),
            SimpleNamespace(
                id=2,
                line_no=2,
                standard_process_name="电泳（盐雾试验要求≤244H）",
                process_token=None,
                process_qty=Decimal("1"),
                unit_price=Decimal("3"),
                line_fee=Decimal("3"),
                match_status="matched",
            ),
        ],
    )
    card = _card(
        items=[],
        welding_fee_id=4,
        welding_amount=Decimal("6"),
        welding_other_fee=Decimal("1"),
        stamping_amount=Decimal("0"),
        material_amount=Decimal("0"),
        total_amount=Decimal("7"),
    )
    bundle = _bundle()
    bundle.welding_fees[4] = fee
    lines = build_object_lines(_hit(), card, bundle)
    weld = [line for line in lines if line.row_type == "焊接"]
    assert weld[0].weld_amount == Decimal("2")
    assert weld[0].ecoat_amount is None
    assert weld[1].ecoat_amount == Decimal("3")
    assert weld[1].weld_amount is None
    other = next(line for line in lines if line.row_type == "其它费用")
    assert OTHER_FEE_NOTE in (other.remark or "")
    total = lines[-1]
    assert total.weld_amount == Decimal("5")
    assert total.line_amount == Decimal("7")
    assert total.remark is None or MISMATCH not in total.remark


def test_export_writes_numbers_and_header_note() -> None:
    lines = build_object_lines(_hit(), _card(), _bundle([_cost()]))
    content = write_workbook(lines, qa_note="检测未通过")
    book = load_workbook(BytesIO(content))
    sheet = book["采购对象"]
    assert sheet["A1"].value == "检测未通过"
    assert sheet["A2"].value == "供应商"
    amount_cell = None
    for row in sheet.iter_rows(min_row=3, max_row=sheet.max_row):
        if row[8].value == "合计":
            amount_cell = row[7]
            break
    assert amount_cell is not None
    assert type(amount_cell.value) is not str
    assert amount_cell.value == 20
    assert export_filename("河西", 2026, 1, None) == "成本还原-采购对象-河西-2026年1月.xlsx"
    assert export_filename("河西", 2026, 1, "J52") == "成本还原-采购对象-河西-J52-2026年1月.xlsx"
