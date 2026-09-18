"""料片四列全空 → 废料副产品；工序比例一律 0；计算层不报失败。"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from app.common.audit import SYSTEM_USER
from app.common.scrap_byproduct import OFFAL_SOURCE_FAMILY_DIE, resolve_scrap_byproduct
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.schemas.dto.stamping_die_fee_dto import StampingDieFeeCalcDTO
from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeFailedItemVO
from app.services.stamping.die_fee.calc.orchestrator.batch_engine import BatchCalculationEngine
from app.services.stamping.die_fee.calc.orchestrator.identity import is_scrap_byproduct_die_part
from app.services.stamping.die_fee.calc.orchestrator.prep import CalcPrepContext
from app.services.stamping.die_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.stamping.die_fee.calc.part_calculator import DieFeePartCalculator
from app.services.stamping.process_fee.calc.part_calculator import PartFeeCalculator
from app.services.stamping.upload.cost_ratio_preserver import ProcessCostRatioPreserver


def test_four_blank_columns_with_weight_is_scrap_byproduct() -> None:
    mark = resolve_scrap_byproduct(
        part_number="502018924AA",
        part_weight=Decimal("0.079"),
        sheet_length=None,
        sheet_width=None,
        parts_per_sheet=0,
        raw_sheet_type=None,
        is_offal_nested=False,
        offal_source=None,
    )
    assert mark.is_scrap_byproduct is True
    assert mark.is_offal_nested is True
    assert mark.offal_source == OFFAL_SOURCE_FAMILY_DIE


def test_blank_length_only_is_not_scrap_byproduct() -> None:
    mark = resolve_scrap_byproduct(
        part_number="502018915AA",
        part_weight=Decimal("2.249"),
        sheet_length=None,
        sheet_width=None,
        parts_per_sheet=1,
        raw_sheet_type="梯形",
        is_offal_nested=False,
        offal_source=None,
    )
    assert mark.is_scrap_byproduct is False
    assert mark.is_offal_nested is False
    assert mark.offal_source is None


def test_offal_phrase_is_not_scrap_byproduct() -> None:
    mark = resolve_scrap_byproduct(
        part_number="502007709AA",
        part_weight=Decimal("0.16"),
        sheet_length=None,
        sheet_width=None,
        parts_per_sheet=0,
        raw_sheet_type="利用侧围废料",
        is_offal_nested=True,
        offal_source="侧围",
    )
    assert mark.is_scrap_byproduct is False
    assert mark.is_offal_nested is True
    assert mark.offal_source == "侧围"


def test_host_blank_with_full_sheet_is_not_scrap() -> None:
    mark = resolve_scrap_byproduct(
        part_number="502018915AA",
        part_weight=Decimal("2.249"),
        sheet_length=Decimal("1150"),
        sheet_width=Decimal("810"),
        parts_per_sheet=1,
        raw_sheet_type="梯形",
        is_offal_nested=False,
        offal_source=None,
    )
    assert mark.is_scrap_byproduct is False


def test_scrap_byproduct_cost_ratio_is_zero_and_overrides_existing() -> None:
    parsed_part = Part(
        part_number="502018924AA",
        part_weight=Decimal("0.079"),
        is_scrap_byproduct=True,
        process_method="合并",
    )
    parsed_process = Process(
        part_number="502018924AA",
        process_seq="OP10",
        process_code="合并",
        cost_ratio=Decimal("1.00"),
    )
    existing = SimpleNamespace(
        process_seq="OP10",
        cost_ratio=Decimal("0.50"),
        part=SimpleNamespace(part_number="502018924AA"),
    )
    ProcessCostRatioPreserver().apply([parsed_process], [existing], [parsed_part])
    assert parsed_process.cost_ratio == Decimal("0.00")


def test_scrap_byproduct_process_fee_is_zero_not_failed() -> None:
    part = SimpleNamespace(
        part_number="502018924AA",
        part_name="左D柱下隔板",
        is_scrap_byproduct=True,
        processes=[SimpleNamespace(id=1, process_seq="OP10", process_code="合并")],
    )
    result = PartFeeCalculator().calc_part_fee(part, {}, 2026)
    assert not isinstance(result, StampingProcessFeeFailedItemVO)
    fee, process_count, items = result
    assert fee == Decimal("0.000")
    assert process_count == 1
    assert items == []


def test_scrap_die_part_matches_identity_key() -> None:
    part = SimpleNamespace(
        stamping_supplier="烟台海众",
        version="V1",
        part_number="502018924AA",
    )
    keys = frozenset({("烟台海众", "V1", "502018924AA")})
    assert is_scrap_byproduct_die_part(part, keys) is True
    assert is_scrap_byproduct_die_part(part, frozenset()) is False


def test_die_fee_batch_skips_scrap_and_keeps_previous_weights() -> None:
    host = SimpleNamespace(
        id=1,
        location="烟台",
        vehicle_model="T2AA",
        stamping_supplier="烟台海众",
        version="V1",
        part_number="502018915AA",
        seq_no=24,
        part_name="左C柱内板",
        material="HC180Y",
        thickness=Decimal("0.7"),
        part_weight=Decimal("2.249"),
        sheet_length=Decimal("1150"),
        sheet_width=Decimal("810"),
        parts_per_sheet=1,
        sheet_shape="梯形",
        die_type="铸造模",
        die_method="双槽",
        production_mode="自动化",
        part_grade="B",
        excel_filename="t.xlsx",
        processes=[
            SimpleNamespace(
                id=11,
                process_seq="OP10",
                process_order=1,
                process_code="DR",
                estimated_weight_t=Decimal("2"),
                alloc_ratio=Decimal("0.50"),
                die_sets=1,
                die_length=Decimal("100"),
                die_width=Decimal("80"),
                die_height=Decimal("50"),
                die_number="T2AA-OP10",
            )
        ],
    )
    scrap = SimpleNamespace(
        id=2,
        location="烟台",
        vehicle_model="T2AA",
        stamping_supplier="烟台海众",
        version="V1",
        part_number="502018924AA",
        seq_no=26,
        part_name="左D柱下隔板",
        material="HC180Y",
        thickness=Decimal("0.7"),
        part_weight=Decimal("0.079"),
        sheet_length=None,
        sheet_width=None,
        parts_per_sheet=None,
        sheet_shape=None,
        die_type=None,
        die_method=None,
        production_mode=None,
        part_grade=None,
        excel_filename="t.xlsx",
        processes=[
            SimpleNamespace(
                id=22,
                process_seq="OP10",
                process_order=1,
                process_code="合并",
                estimated_weight_t=None,
                alloc_ratio=Decimal("0.50"),
                die_sets=1,
                die_length=None,
                die_width=None,
                die_height=None,
            )
        ],
    )
    price = SimpleNamespace(
        steel_plate_unit_price=Decimal("5"),
        progressive_die_unit_price=Decimal("6"),
        allocation_qty=Decimal("10"),
    )
    ctx = CalcPrepContext(
        parts=[host, scrap],
        persist_parts=[host, scrap],
        price=price,
        started_at=datetime(2026, 9, 2),
        detail_lines=[],
        scrap_byproduct_keys=frozenset({("烟台海众", "V1", "502018924AA")}),
    )
    dto = StampingDieFeeCalcDTO(year=2026, location="烟台", vehicle_model="T2AA")
    outcome = BatchCalculationEngine(DieFeePartCalculator()).run(
        ctx=ctx,
        dto=dto,
        current_user=SYSTEM_USER,
        progress=ProgressNotifier(),
    )
    assert outcome.success_count == 1
    assert outcome.skipped_no_die_count == 1
    assert outcome.insert_rows[0].part_number == "502018915AA"


def test_die_fee_batch_skips_scrap_from_blank_sheet_layout() -> None:
    """未传工艺表时，布点四列全空仍跳过副产品、不继承重量。"""
    host = SimpleNamespace(
        id=1,
        location="青岛",
        vehicle_model="T2AA",
        stamping_supplier=None,
        version=None,
        part_number="502018915AA",
        seq_no=24,
        part_name="左C柱内板",
        material="HC180Y",
        thickness=Decimal("0.7"),
        part_weight=Decimal("2.249"),
        sheet_length=Decimal("1150"),
        sheet_width=Decimal("810"),
        parts_per_sheet=1,
        sheet_shape="梯形",
        die_type="铸造模",
        die_method="双槽",
        production_mode="自动化",
        part_grade="B",
        excel_filename="t.xlsx",
        processes=[
            SimpleNamespace(
                id=11,
                process_seq="OP10",
                process_order=1,
                process_code="DR",
                estimated_weight_t=Decimal("2"),
                alloc_ratio=Decimal("0.50"),
                die_sets=1,
                die_length=Decimal("100"),
                die_width=Decimal("80"),
                die_height=Decimal("50"),
                die_number="T2AA-OP10",
            )
        ],
    )
    scrap = SimpleNamespace(
        id=2,
        location="青岛",
        vehicle_model="T2AA",
        stamping_supplier=None,
        version=None,
        part_number="502018924AA",
        seq_no=26,
        part_name="左D柱下隔板",
        material="HC180Y",
        thickness=Decimal("0.7"),
        part_weight=Decimal("0.079"),
        sheet_length=None,
        sheet_width=None,
        parts_per_sheet=None,
        sheet_shape=None,
        die_type=None,
        die_method="双槽",
        production_mode=None,
        part_grade=None,
        excel_filename="t.xlsx",
        processes=[
            SimpleNamespace(
                id=22,
                process_seq="OP10",
                process_order=1,
                process_code="合并",
                estimated_weight_t=None,
                alloc_ratio=Decimal("0.50"),
                die_sets=1,
                die_length=None,
                die_width=None,
                die_height=None,
            )
        ],
    )
    price = SimpleNamespace(
        steel_plate_unit_price=Decimal("5"),
        progressive_die_unit_price=Decimal("6"),
        allocation_qty=Decimal("10"),
    )
    ctx = CalcPrepContext(
        parts=[host, scrap],
        persist_parts=[host, scrap],
        price=price,
        started_at=datetime(2026, 9, 2),
        detail_lines=[],
        scrap_byproduct_keys=frozenset(),
    )
    dto = StampingDieFeeCalcDTO(year=2026, location="青岛", vehicle_model="T2AA")
    outcome = BatchCalculationEngine(DieFeePartCalculator()).run(
        ctx=ctx,
        dto=dto,
        current_user=SYSTEM_USER,
        progress=ProgressNotifier(),
    )
    assert outcome.success_count == 1
    assert outcome.skipped_no_die_count == 1
    assert outcome.insert_rows[0].part_number == "502018915AA"
