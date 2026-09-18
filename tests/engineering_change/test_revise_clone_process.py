"""改图换号：冲压零件除号/版本/生失效外整行抄旧号，工序相同。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.parsers.stamping.models.part import Part
from app.services.engineering_change.upload.persist.process import (
    _part_from_confirmation_sheet,
)
from app.services.stamping.part.engineering_change import clone_revise_part_payload


def test_revise_clones_part_and_identical_processes() -> None:
    old_part = SimpleNamespace(
        location="青岛",
        vehicle_model="T28",
        version="D/00",
        stamping_supplier="烟台海众汽车零部件有限公司",
        seq_no=70,
        part_number="501006875AA",
        part_name="雨刮电机安装支架Ⅰ",
        material="DC51D+Z",
        thickness=Decimal("1.2000"),
        part_weight=Decimal("0.0960"),
        sheet_length=Decimal("165.00"),
        sheet_width=Decimal("122.00"),
        parts_per_sheet=1,
        sheet_type="卷料",
        is_offal_nested=False,
        offal_source=None,
        is_scrap_byproduct=False,
        has_swing_shear=True,
        die_type="钢板模",
        process_method="级进模",
        automation="自动",
        remark="旧备注",
        sketch_url="T28/875AA.png",
        is_tailor_welded=False,
        excel_filename="T28项目车身件初版材料清单.xlsx",
        excel_sheet_name="材料清单",
        excel_row=18,
        excel_part_col=3,
    )
    old_processes = [
        SimpleNamespace(
            process_seq="OP10",
            process_order=1,
            die_sets=1,
            process_code="PRG",
            die_number="M-875",
            tonnage=315,
            cost_ratio=Decimal("0.80"),
            remark="共模",
        ),
        SimpleNamespace(
            process_seq="OP20",
            process_order=2,
            die_sets=2,
            process_code="TR",
            die_number=None,
            tonnage=250,
            cost_ratio=Decimal("0.50"),
            remark=None,
        ),
    ]
    part_data, processes = clone_revise_part_payload(
        old_part,
        old_processes,
        new_part_number="501006875AB",
        version="EC-202507",
        effective_year=2025,
        effective_month=7,
        expiry_year=None,
        expiry_month=None,
        created_by="tester",
        updated_by="tester",
    )
    assert part_data.part_number == "501006875AB"
    assert part_data.version == "EC-202507"
    assert part_data.effective_year == 2025
    assert part_data.effective_month == 7
    assert part_data.seq_no == 70
    assert part_data.part_name == "雨刮电机安装支架Ⅰ"
    assert part_data.material == "DC51D+Z"
    assert part_data.thickness == Decimal("1.2000")
    assert part_data.part_weight == Decimal("0.0960")
    assert part_data.sheet_length == Decimal("165.00")
    assert part_data.sheet_width == Decimal("122.00")
    assert part_data.parts_per_sheet == 1
    assert part_data.sheet_type == "卷料"
    assert part_data.has_swing_shear is True
    assert part_data.die_type == "钢板模"
    assert part_data.process_method == "级进模"
    assert part_data.automation == "自动"
    assert part_data.remark == "旧备注"
    assert part_data.sketch_url is None
    assert part_data.stamping_supplier == "烟台海众汽车零部件有限公司"
    assert part_data.excel_filename == "T28项目车身件初版材料清单.xlsx"
    assert part_data.excel_sheet_name == "材料清单"
    assert part_data.excel_row == 18
    assert part_data.excel_part_col == 3
    assert len(processes) == 2
    assert processes[0].process_seq == "OP10"
    assert processes[0].process_code == "PRG"
    assert processes[0].die_number == "M-875"
    assert processes[0].tonnage == 315
    assert processes[0].cost_ratio == Decimal("0.80")
    assert processes[0].die_sets == 1
    assert processes[1].process_seq == "OP20"
    assert processes[1].process_order == 2
    assert processes[1].cost_ratio == Decimal("0.50")
    assert processes[1].die_sets == 2


def test_save_process_sketches_writes_png(tmp_path, monkeypatch) -> None:
    from app.config import settings
    from app.services.stamping.upload.persist.files import save_part_sketches

    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x00\x03\x00\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    urls = save_part_sketches(
        {"501007040AA": png},
        location="青岛",
        vehicle_model="T28",
        version="EC-202507",
    )
    relative = "青岛/T28/EC-202507/501007040AA.png"
    assert urls["501007040AA"] == relative
    saved = tmp_path / "青岛" / "T28" / "EC-202507" / "501007040AA.png"
    assert saved.read_bytes() == png


def test_t2aa_process_sheet_keeps_revised_part_sketch() -> None:
    from pathlib import Path

    from app.parsers.engineering_change.sheet_extract import SHEET_PROCESS
    from app.parsers.stamping.stamping_parser import parse_stamping_excel

    sample = Path("docs/engineering-change/samples/工程变更导入T2AA-1.xlsx")
    parsed = parse_stamping_excel(str(sample), sheet_title=SHEET_PROCESS)
    png = parsed.images_by_part.get("551005982AB")
    assert png, "合册工艺确认表 5982AB 必须抽出零件简图，不能落到旧号图上"
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_revise_remaps_tailor_weld_blank_part_number() -> None:
    from app.services.stamping.part.engineering_change import _remapped_blank_part_number

    assert (
        _remapped_blank_part_number(
            old_parent="501006875AA",
            new_parent="501006875AB",
            blank_part_number="501006875AA-1",
            blank_seq=1,
        )
        == "501006875AB-1"
    )
    assert (
        _remapped_blank_part_number(
            old_parent="501006875AA",
            new_parent="501006875AB",
            blank_part_number="OTHER-1",
            blank_seq=2,
        )
        == "501006875AB-2"
    )


def test_add_part_from_sheet_uses_assigned_seq_not_excel() -> None:
    parsed = Part(seq_no=1, part_number="501009999AA", part_name="新件")
    part_data, processes = _part_from_confirmation_sheet(
        parsed_part=parsed,
        all_processes=[],
        location="青岛",
        vehicle_model="T28",
        version="EC-202507",
        supplier="烟台海众汽车零部件有限公司",
        seq_no=71,
        effective_year=2025,
        effective_month=7,
        expiry_year=None,
        expiry_month=None,
        created_by="tester",
        updated_by="tester",
    )
    assert part_data.seq_no == 71
    assert part_data.part_number == "501009999AA"
    assert part_data.excel_row is None
    assert part_data.excel_sheet_name is None
    assert processes == []
