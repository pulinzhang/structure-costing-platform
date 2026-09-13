"""布点缺号按 DP-40-{项目}-流水补号。"""

from decimal import Decimal

import pytest

from app.exceptions.base import BusinessException
from app.parsers.stamping.die.parser import ParsedDiePart, ParsedDieProcess
from app.services.stamping.die.die_number_assigner import assign_die_numbers


def _process(**overrides: object) -> ParsedDieProcess:
    payload: dict[str, object] = {
        "process_seq": "OP10",
        "process_code": "拉伸",
        "die_sets": 1,
        "die_number": None,
        "die_length": Decimal("100"),
        "die_width": Decimal("80"),
        "die_height": Decimal("50"),
        "hollow_factor": None,
        "estimated_weight_t": None,
        "tonnage": None,
        "excel_row": 10,
    }
    payload.update(overrides)
    return ParsedDieProcess(**payload)  # type: ignore[arg-type]


def _part(*processes: ParsedDieProcess, part_number: str = "50200111AA") -> ParsedDiePart:
    return ParsedDiePart(
        seq_no=1,
        part_number=part_number,
        part_name="内板",
        material=None,
        thickness=None,
        part_weight=None,
        sheet_length=None,
        sheet_width=None,
        sheet_shape=None,
        parts_per_sheet=None,
        material_consumption=None,
        material_utilization=None,
        estimated_weight_subtotal_t=None,
        die_type=None,
        die_method=None,
        production_mode=None,
        needs_end_effector=None,
        part_grade=None,
        remark=None,
        excel_sheet_name="零件汇总",
        excel_row=6,
        excel_part_col=2,
        processes=list(processes),
    )


def test_assign_starts_at_001() -> None:
    result = assign_die_numbers(
        vehicle_model="T13J",
        parts=[_part(_process())],
        existing_numbers=[],
    )
    assert result.assigned_count == 1
    assert result.by_key[("50200111AA", "OP10")] == "DP-40-T13J-001"


def test_assign_continues_after_427() -> None:
    result = assign_die_numbers(
        vehicle_model="T13J",
        parts=[_part(_process())],
        existing_numbers=["DP-40-T13J-427"],
    )
    assert result.by_key[("50200111AA", "OP10")] == "DP-40-T13J-428"


def test_assign_skips_non_rule_numbers() -> None:
    result = assign_die_numbers(
        vehicle_model="T13J",
        parts=[_part(_process())],
        existing_numbers=["T13J-OP10-001", "OTHER-40-T13J-900"],
    )
    assert result.by_key[("50200111AA", "OP10")] == "DP-40-T13J-001"


def test_shared_without_size_not_assigned() -> None:
    result = assign_die_numbers(
        vehicle_model="T13J",
        parts=[
            _part(
                _process(
                    process_code="共用",
                    die_length=None,
                    die_width=None,
                    die_height=None,
                )
            )
        ],
        existing_numbers=[],
    )
    assert result.assigned_count == 0
    assert result.by_key[("50200111AA", "OP10")] is None


def test_keeps_excel_number() -> None:
    result = assign_die_numbers(
        vehicle_model="T13J",
        parts=[_part(_process(die_number="DP-40-T13J-010"))],
        existing_numbers=[],
    )
    assert result.assigned_count == 0
    assert result.by_key[("50200111AA", "OP10")] == "DP-40-T13J-010"


def test_full_serial_range_fails() -> None:
    occupied = [f"DP-40-T13J-{index:03d}" for index in range(1, 1000)]
    with pytest.raises(BusinessException, match="已满"):
        assign_die_numbers(
            vehicle_model="T13J",
            parts=[_part(_process())],
            existing_numbers=occupied,
        )
