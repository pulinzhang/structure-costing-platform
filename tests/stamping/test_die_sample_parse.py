"""可选：解析 T13J 模具布点样本（文件不在仓库时跳过）。"""

from decimal import Decimal
from pathlib import Path

import pytest

from app.parsers.stamping.die.parser import (
    ParsedDiePart,
    ParsedDieProcess,
    _vehicle_from_text,
    layout_has_die_mass,
    parse_die_layout_excel,
)
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


_T2AA_SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "excel_sample"
    / "T2AA"
    / "T2AA项目冲压模具布点工艺清单.xlsx"
)
_skip_t2aa = pytest.mark.skipif(
    not _T2AA_SAMPLE.is_file(), reason="T2AA 布点样本未放入 excel_sample"
)


@_skip_t2aa
def test_parse_t2aa_die_layout_process_seq_header() -> None:
    """T2AA：二级表头「工序」换行「名称」，模具尺寸列为「模具长/宽/高」。"""
    result = parse_die_layout_excel(str(_T2AA_SAMPLE), filename=_T2AA_SAMPLE.name)
    assert result.vehicle_model == "T2AA"
    assert result.parts
    first = next(part for part in result.parts if part.part_number == "501029963AA")
    assert first.part_name == "后围内板"
    assert first.material == "DC01"
    assert [item.process_seq for item in first.processes] == ["OP10", "OP20", "OP30", "OP40"]
    assert first.processes[0].process_code == "DR"
    assert first.die_method == "单干"
    host = next(part for part in result.parts if part.part_number == "502018915AA")
    scrap = next(part for part in result.parts if part.part_number == "502018924AA")
    assert host.is_scrap_byproduct is False
    assert scrap.is_scrap_byproduct is True
    assert scrap.sheet_length is None
    assert scrap.sheet_width is None
    assert scrap.parts_per_sheet is None
    assert scrap.sheet_shape is None
    assert scrap.processes[0].process_code == "合并"
    weighted = sum(
        1
        for part in result.parts
        for process in part.processes
        if process.estimated_weight_t is not None and process.estimated_weight_t > Decimal("0")
    )
    assert weighted >= 1
    assert layout_has_die_mass(result.parts) is True


_T2AA_PROCESS_STYLE = (
    Path(__file__).resolve().parents[2]
    / "excel_sample"
    / "T2AA"
    / "T2AA项目冲压模具布点工艺清单（加凸焊信息)V0-01-2026-08-18（模版）(1).xlsx"
)
_skip_t2aa_process_style = pytest.mark.skipif(
    not _T2AA_PROCESS_STYLE.is_file(), reason="T2AA 凸焊工艺表样本未放入 excel_sample"
)


@_skip_t2aa_process_style
def test_parse_t2aa_process_style_file_has_aliases_but_no_die_mass() -> None:
    result = parse_die_layout_excel(str(_T2AA_PROCESS_STYLE), filename=_T2AA_PROCESS_STYLE.name)
    first = next(part for part in result.parts if part.part_number == "501029963AA")
    assert first.part_weight == Decimal("1.1310")
    assert first.sheet_shape == "方料"
    assert first.production_mode == "Transfer"
    assert first.processes[0].die_length is None
    assert first.processes[0].estimated_weight_t is None
    assert layout_has_die_mass(result.parts) is False


def _empty_mass_process() -> ParsedDieProcess:
    return ParsedDieProcess(
        process_seq="OP10",
        process_code="DR",
        die_sets=1,
        die_number=None,
        die_length=None,
        die_width=None,
        die_height=None,
        hollow_factor=None,
        estimated_weight_t=None,
        tonnage=1600,
    )


def test_layout_has_die_mass_requires_weight_or_size() -> None:
    empty = ParsedDiePart(
        seq_no=1,
        part_number="501029963AA",
        part_name="后围内板",
        material=None,
        thickness=None,
        part_weight=Decimal("1.1310"),
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
        excel_sheet_name=None,
        excel_row=1,
        excel_part_col=2,
        processes=[_empty_mass_process()],
    )
    assert layout_has_die_mass([empty]) is False
    empty.processes[0].estimated_weight_t = Decimal("2.0000")
    assert layout_has_die_mass([empty]) is True


def test_die_layout_title_extracts_vehicle() -> None:
    assert _vehicle_from_text("T2AA项目冲压模具布点工艺清-20260818") == "T2AA"
    assert _vehicle_from_text("副本②T13J项目冲压模具布点工艺清单-2024-01-22.xlsx") == "T13J"
    assert _vehicle_from_text("T28项目冲压工艺确认表-V1") is None
