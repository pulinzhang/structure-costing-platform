"""工程变更查数：列表零件 / 新旧号 / 停用件。"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.common.engineering_change_gates import CHANGE_TYPE_NOT_INSTALL, CHANGE_TYPE_STOP
from app.repositories.llm.cost_analysis import L0PartPeriodRow
from app.repositories.llm.engineering_change_analysis_repository import EngineeringChangeRow
from app.repositories.llm.procurement_object_analysis_repository import ProcurementObjectRow
from app.services.llm.analysis.ops.engineering_change import (
    build_ec_procurement_supplier_status,
    build_engineering_change_drilldown,
    build_engineering_change_price_comparison,
    build_engineering_change_risks,
    build_engineering_change_summary,
    price_window_for_rows,
)
from app.services.llm.query.intent_router import detect_query_mode
from app.services.llm.query.parser.subjects import (
    asks_ec_procurement_supplier_status,
    asks_engineering_change_discontinue,
    asks_engineering_change_price_compare,
    resolve_subject,
)


@pytest.mark.parametrize(
    ("question", "expected_mode"),
    [
        ("2025年，工程变更那些零件", "analysis"),
        ("工程变更有哪些零件", "analysis"),
        ("501006875AB 工程变更前叫什么", "analysis"),
        ("这个件变更前零件号是什么", "analysis"),
        ("有没有停用件", "analysis"),
        ("T13J 有没有此件不装", "analysis"),
        ("完成停止有哪些", "analysis"),
        ("工程变更改图了哪些", "analysis"),
        ("设变了哪些总成", "analysis"),
        ("给我一下，工程变更零件的单价，进行变更前和变更后单价比较", "analysis"),
        ("设变件供应商的指定情况", "analysis"),
        ("增加零件有没有指定供应商", "analysis"),
        ("设变后哪些外发还没指定厂家", "analysis"),
        ("设变后哪些总成应成本涨超10%", "analysis"),
        ("设变后采购对象插齐了没有", "analysis"),
        ("改图后有没有模具布点", "analysis"),
        ("工程变更怎么上传？", "usage_help"),
        ("此件不装怎么填", "usage_help"),
        ("投产后改图换号走哪里？", "usage_help"),
        ("设变从哪个月开始算新零件", "usage_help"),
        ("这个月核价用旧号还是新号", "usage_help"),
    ],
)
def test_engineering_change_query_mode(question: str, expected_mode: str) -> None:
    assert detect_query_mode(question) == expected_mode


@pytest.mark.parametrize(
    ("question", "expected_subject"),
    [
        ("2025年，工程变更那些零件", "engineering_change"),
        ("501006875AB 工程变更前叫什么", "engineering_change"),
        ("有没有停用件", "engineering_change"),
        ("此件不装有哪些", "engineering_change"),
        ("对应旧号是什么", "engineering_change"),
        ("给我一下，工程变更零件的单价，进行变更前和变更后单价比较", "engineering_change"),
        ("设变件供应商的指定情况", "engineering_change"),
        ("增加零件有没有指定供应商", "engineering_change"),
    ],
)
def test_engineering_change_subject(question: str, expected_subject: str) -> None:
    assert resolve_subject(question=question, analyses=["summary"], filters={}) == expected_subject


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("有没有停用件", True),
        ("此件不装有哪些", True),
        ("完成停止哪些总成", True),
        ("工程变更那些零件", False),
        ("变更前叫什么", False),
    ],
)
def test_asks_discontinue(question: str, expected: bool) -> None:
    assert asks_engineering_change_discontinue(question) is expected


def _row(
    *,
    change_type: str,
    before_part: str | None = None,
    after_part: str | None = None,
    before_assembly: str = "501008897AA",
    after_assembly: str | None = "501008897AB",
) -> EngineeringChangeRow:
    return EngineeringChangeRow(
        location="青岛",
        vehicle_model="T28",
        effective_year=2025,
        effective_month=7,
        change_type=change_type,
        before_assembly_part_number=before_assembly,
        after_assembly_part_number=after_assembly,
        assembly_name="后围总成",
        part_level="一级",
        before_part_number=before_part,
        after_part_number=after_part,
        part_name="胶块",
        project_code="T28",
        status="active",
    )


def test_summary_separates_stop_and_not_install() -> None:
    rows = [
        _row(change_type=CHANGE_TYPE_STOP, before_assembly="501009533AA", after_assembly=None),
        _row(
            change_type=CHANGE_TYPE_NOT_INSTALL,
            before_part="504000341AA",
            after_part=None,
        ),
        _row(change_type="改图", before_part="501006875AA", after_part="501006875AB"),
    ]
    summary = build_engineering_change_summary(rows)
    assert summary["row_count"] == 3
    assert summary["stop_count"] == 1
    assert summary["not_install_count"] == 1
    assert summary["discontinue_count"] == 2
    risks = build_engineering_change_risks(summary)
    assert len(risks["risks"]) == 2


def test_asks_price_compare() -> None:
    assert asks_engineering_change_price_compare(
        "给我一下，工程变更零件的单价，进行变更前和变更后单价比较"
    )
    assert asks_engineering_change_price_compare("设变后哪些总成应成本涨超10%")
    assert not asks_engineering_change_price_compare("工程变更那些零件")


def test_asks_ec_procurement_supplier_status() -> None:
    assert asks_ec_procurement_supplier_status("设变件供应商的指定情况")
    assert asks_ec_procurement_supplier_status("增加零件有没有指定供应商")
    assert not asks_ec_procurement_supplier_status("哪一个采购对象没有供应商")


def test_summary_by_level_and_stop_assembly_count() -> None:
    rows = [
        _row(change_type=CHANGE_TYPE_STOP, before_assembly="501009533AA", after_assembly=None),
        _row(
            change_type=CHANGE_TYPE_NOT_INSTALL,
            before_part="504000341AA",
            after_part=None,
        ),
        _row(change_type="改图", before_part="501006875AA", after_part="501006875AB"),
    ]
    summary = build_engineering_change_summary(rows)
    assert summary["change_type_by_level"]["一级"]["改图"] == 1
    assert summary["stop_assembly_count"] == 1


def test_ec_procurement_supplier_status_four_buckets() -> None:
    rows = [
        _row(change_type="增加零件", before_part=None, after_part="NEW-MISS"),
        _row(change_type="改图", before_part="OLD-OK", after_part="NEW-OK"),
        _row(change_type="增加零件", before_part=None, after_part="NEW-PENDING"),
        _row(change_type="改图", before_part="OLD-GONE", after_part="NEW-ABSENT"),
        _row(
            change_type=CHANGE_TYPE_NOT_INSTALL,
            before_part="SKIP-ME",
            after_part=None,
        ),
    ]
    procurement = [
        ProcurementObjectRow(
            location="青岛",
            vehicle_model="T28",
            bom_version="D/00",
            part_number="NEW-MISS",
            part_name="缺厂家",
            section="normal",
            object_kind="stamping",
            confirm_status="outsourced",
            audit_status="pending",
            supplier_name=None,
        ),
        ProcurementObjectRow(
            location="青岛",
            vehicle_model="T28",
            bom_version="D/00",
            part_number="NEW-OK",
            part_name="已指定",
            section="normal",
            object_kind="stamping",
            confirm_status="outsourced",
            audit_status="approved",
            supplier_name="甲厂",
        ),
        ProcurementObjectRow(
            location="青岛",
            vehicle_model="T28",
            bom_version="D/00",
            part_number="NEW-PENDING",
            part_name="待确认",
            section="normal",
            object_kind="stamping",
            confirm_status="pending",
            audit_status="pending",
            supplier_name=None,
        ),
    ]
    payload = build_ec_procurement_supplier_status(rows, procurement)
    assert payload["ec_part_count"] == 4
    assert payload["missing_supplier_count"] == 1
    assert payload["with_supplier_count"] == 1
    assert payload["pending_confirm_count"] == 1
    assert payload["not_in_procurement_count"] == 1
    assert payload["missing_supplier_items"][0]["part_number"] == "NEW-MISS"
    assert all(
        item["change_type"] != CHANGE_TYPE_NOT_INSTALL
        for item in payload["not_in_procurement_items"]
    )


def test_price_window_for_rows() -> None:
    rows = [_row(change_type="改图", before_part="A", after_part="B")]
    window = price_window_for_rows(rows)
    assert window == (2024, 7, 2026, 7)


def test_price_comparison_before_after() -> None:
    rows = [_row(change_type="改图", before_part="501006875AA", after_part="501006875AB")]
    before = L0PartPeriodRow(
        year=2025,
        month=6,
        part_number="501006875AA",
        part_name="旧件",
        grand_total=Decimal("12.00"),
        total_amount=Decimal("10.00"),
        calc_status="ok",
        missing_leaf_count=0,
        calc_message=None,
        stamping_amount=Decimal("0"),
        purchased_amount=Decimal("0"),
        bundle_amount=Decimal("0"),
        welding_amount=Decimal("0"),
        welding_other_fee=Decimal("0"),
        indirect_amount=Decimal("0"),
        bom_version="V1",
        should_cost=Decimal("10.50"),
    )
    after = L0PartPeriodRow(
        year=2025,
        month=7,
        part_number="501006875AB",
        part_name="新件",
        grand_total=Decimal("13.00"),
        total_amount=Decimal("11.00"),
        calc_status="ok",
        missing_leaf_count=0,
        calc_message=None,
        stamping_amount=Decimal("0"),
        purchased_amount=Decimal("0"),
        bundle_amount=Decimal("0"),
        welding_amount=Decimal("0"),
        welding_other_fee=Decimal("0"),
        indirect_amount=Decimal("0"),
        bom_version="EC-202507",
        should_cost=Decimal("11.20"),
    )
    payload = build_engineering_change_price_comparison(
        rows,
        assembly_by_part={
            "501006875AA": [before],
            "501006875AB": [after],
        },
        stamping_by_part={},
    )
    assert payload["both_priced_count"] == 1
    item = payload["items"][0]
    assert item["before"]["unit_price"] == "10.50"
    assert item["after"]["unit_price"] == "11.20"
    assert item["delta"] == "0.70"
    assert payload["after_priced_count"] == 1


def test_price_comparison_jump_up() -> None:
    rows = [_row(change_type="改图", before_part="501006875AA", after_part="501006875AB")]
    before = L0PartPeriodRow(
        year=2025,
        month=6,
        part_number="501006875AA",
        part_name="旧件",
        grand_total=Decimal("10.00"),
        total_amount=Decimal("10.00"),
        calc_status="ok",
        missing_leaf_count=0,
        calc_message=None,
        stamping_amount=Decimal("4.00"),
        purchased_amount=Decimal("3.00"),
        bundle_amount=Decimal("0"),
        welding_amount=Decimal("2.00"),
        welding_other_fee=Decimal("0"),
        indirect_amount=Decimal("1.00"),
        bom_version="V1",
        should_cost=Decimal("10.00"),
    )
    after = L0PartPeriodRow(
        year=2025,
        month=7,
        part_number="501006875AB",
        part_name="新件",
        grand_total=Decimal("12.00"),
        total_amount=Decimal("12.00"),
        calc_status="ok",
        missing_leaf_count=0,
        calc_message=None,
        stamping_amount=Decimal("5.50"),
        purchased_amount=Decimal("3.00"),
        bundle_amount=Decimal("0"),
        welding_amount=Decimal("2.00"),
        welding_other_fee=Decimal("0"),
        indirect_amount=Decimal("1.50"),
        bom_version="EC-202507",
        should_cost=Decimal("12.00"),
    )
    payload = build_engineering_change_price_comparison(
        rows,
        assembly_by_part={
            "501006875AA": [before],
            "501006875AB": [after],
        },
        stamping_by_part={},
    )
    assert payload["jump_up_count"] == 1
    assert payload["jump_up_items"][0]["is_jump_up"] is True
    assert payload["items"][0]["composition_delta"]["stamping_amount"] == "1.50"


def test_drilldown_alias_before_after() -> None:
    rows = [_row(change_type="改图", before_part="501006875AA", after_part="501006875AB")]
    payload = build_engineering_change_drilldown(rows, part_token="501006875AB", head=rows[0])
    assert payload["found"] is True
    assert payload["alias_before"] == "501006875AA"
    assert payload["alias_after"] == "501006875AB"
