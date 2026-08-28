"""可选：解析 T13J 模具布点样本（文件不在仓库时跳过）。"""

from decimal import Decimal
from pathlib import Path

import pytest

from app.parsers.stamping_die.parser import _vehicle_from_text, parse_die_layout_excel
from app.services.stamping.process_seq_validator import (
    ProcessSeqOccurrence,
    find_duplicate_process_seqs,
)

_SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "excel_sample"
    / "T13J"
    / "副本②T13J项目冲压模具布点工艺清单-2024-01-22.xlsx"
)

_skip_sample = pytest.mark.skipif(not _SAMPLE.is_file(), reason="样本 Excel 未放入 excel_sample")


@_skip_sample
def test_parse_t13j_die_layout_counts() -> None:
    result = parse_die_layout_excel(str(_SAMPLE), filename=_SAMPLE.name)
    assert result.vehicle_model == "T13J"
    assert len(result.parts) == 88
    process_count = sum(len(part.processes) for part in result.parts)
    assert process_count == 355
    duplicate_seqs = find_duplicate_process_seqs(
        [
            ProcessSeqOccurrence(
                part_number=part.part_number,
                process_seq=process.process_seq,
                excel_row=process.excel_row,
            )
            for part in result.parts
            for process in part.processes
        ]
    )
    assert duplicate_seqs == []

    first = next(part for part in result.parts if part.part_number == "502007709AA")
    op05 = next(item for item in first.processes if item.process_seq == "OP05")
    assert op05.process_code == "BL"
    assert op05.die_length == Decimal("880.00")

    shared = next(part for part in result.parts if part.part_number == "502007733AA")
    shared_op05 = next(item for item in shared.processes if item.process_seq == "OP05")
    assert shared_op05.process_code == "共用"
    assert shared_op05.die_length is None


def test_die_layout_title_extracts_vehicle() -> None:
    assert _vehicle_from_text("T2AA项目冲压模具布点工艺清-20260818") == "T2AA"
    assert _vehicle_from_text("副本②T13J项目冲压模具布点工艺清单-2024-01-22.xlsx") == "T13J"
    assert _vehicle_from_text("T28项目冲压工艺确认表-V1") is None
