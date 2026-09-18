"""改图换号：冲压零件除号/版本/生失效外整行抄旧号，工序相同。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

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
        excel_filename="",
        excel_sheet_name="冲压工艺确认表",
        excel_row=7,
        excel_part_col=3,
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
    assert part_data.sketch_url == "T28/875AA.png"
    assert part_data.stamping_supplier == "烟台海众汽车零部件有限公司"
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
