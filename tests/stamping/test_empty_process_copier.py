"""空工序按 Excel 上一件补齐。"""

from decimal import Decimal

from app.parsers.stamping.empty_process_copier import copy_empty_processes_from_previous
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process


def test_empty_right_part_copies_previous_op10() -> None:
    left = Part(part_number="501044654AA", excel_row=59)
    right = Part(part_number="501044655AA", excel_row=60)
    processes = [
        Process(
            part_number="501044654AA",
            process_seq="OP10",
            process_code="PRG",
            die_sets=1,
            tonnage=500,
            excel_row=59,
        )
    ]
    filled = copy_empty_processes_from_previous([left, right], processes)
    assert filled == ["501044655AA"]
    copied = [item for item in processes if item.part_number == "501044655AA"]
    assert len(copied) == 1
    assert copied[0].process_seq == "OP10"
    assert copied[0].process_code == "PRG"
    assert copied[0].tonnage == 500
    assert copied[0].excel_row == 60


def test_blank_op_rows_are_replaced_not_kept() -> None:
    left = Part(part_number="501044654AA", excel_row=59)
    right = Part(part_number="501044655AA", excel_row=60)
    processes = [
        Process(
            part_number="501044654AA",
            process_seq="OP10",
            process_code="PRG",
            tonnage=500,
            excel_row=59,
        ),
        Process(
            part_number="501044655AA",
            process_seq="OP10",
            process_code="",
            excel_row=60,
        ),
    ]
    copy_empty_processes_from_previous([left, right], processes)
    right_ops = [item for item in processes if item.part_number == "501044655AA"]
    assert len(right_ops) == 1
    assert right_ops[0].process_code == "PRG"
    assert right_ops[0].tonnage == 500


def test_scrap_byproduct_does_not_copy_previous() -> None:
    host = Part(part_number="502018915AA", excel_row=167)
    scrap = Part(
        part_number="502018924AA",
        excel_row=181,
        is_scrap_byproduct=True,
        part_weight=Decimal("0.079"),
    )
    processes = [
        Process(
            part_number="502018915AA",
            process_seq="OP10",
            process_code="DR",
            tonnage=1000,
            excel_row=168,
        )
    ]
    filled = copy_empty_processes_from_previous([host, scrap], processes)
    assert filled == []
    assert all(item.part_number != "502018924AA" for item in processes)
