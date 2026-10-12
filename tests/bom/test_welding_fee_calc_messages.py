from app.services.bom.welding_fee.calc.orchestrator.messages import (
    format_nodes_in_scope,
    format_persist_summary,
    format_prep_opening,
    format_prices_loaded,
)
from app.services.bom.welding_fee.calc.staff_report import calc_finish_toast


def test_welding_fee_calc_copy_is_plain_chinese() -> None:
    opening = format_prep_opening(2026, "芜湖", "T13J")
    prices = format_prices_loaded(13)
    nodes = format_nodes_in_scope(89, [0, 1])
    summary = format_persist_summary(89, 0, 0, 0, 0)
    text = f"{opening}\n{prices}\n{nodes}\n{summary}"

    assert opening == "开始计算：2026年，芜湖，T13J。"
    assert prices == "本年本基地有 13 条焊接单价。"
    assert nodes == "要算 89 个零件，包含供货总成、分总成。"
    assert summary == "新写入焊接费 89 条。没有失败，单价都对上了。"
    assert "year=" not in text
    assert "[" not in text
    assert "拆解节点" not in text
    assert format_nodes_in_scope(10, [0]) == "要算 10 个零件，都是供货总成。"
    assert format_persist_summary(80, 9, 0, 2, 3) == (
        "新写入 80 条，重算 9 条。2 条工艺在本年单价里对不上。3 条已经审核过，这次没重算。"
    )


def test_welding_fee_toast_points_at_the_excel_row() -> None:
    text = calc_finish_toast(
        biz_status="partial",
        created_count=80,
        updated_count=0,
        failed_count=3,
        missing_price_count=0,
        skipped_approved_count=0,
    )
    assert "3 条没算上" in text
    assert "原因写在下面" not in text
    assert "Excel 文件名和第几行" in text
