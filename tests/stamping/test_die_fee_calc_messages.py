from app.services.stamping.die_fee.calc.orchestrator.messages import (
    format_all_skipped_hint,
    format_calc_finished_log,
    format_layout_scope,
    format_persist_summary,
    format_prep_opening,
)


def test_die_fee_calc_copy_is_plain_chinese() -> None:
    assert format_prep_opening(2026, "芜湖", "T13J", None) == (
        "开始计算：2026年，芜湖，T13J，全部工厂"
    )
    assert format_prep_opening(2026, "芜湖", "T13J", "V3") == (
        "开始计算：2026年，芜湖，T13J，全部工厂，版本 V3"
    )
    assert format_layout_scope(88, 88) == "有效期内的模具布点 88 件，这次都要算。"
    assert format_layout_scope(40, 88) == (
        "这次要算 40 件。左右件共用一套模具，对照时看了整份布点 88 件。"
    )
    assert format_persist_summary(48, 40) == (
        "写入模具费 48 件。另外 40 件没写入：没有模具尺寸或重量，算不出钱；家模带出来的小件也不记模具费。"
    )
    assert "year" not in format_prep_opening(2026, "芜湖", "T13J", None)
    assert "系统费" not in format_persist_summary(48, 40)
    assert "工艺确认表" in format_all_skipped_hint()
    assert format_calc_finished_log(2026, "芜湖", "T13J", 48, 40) == (
        "冲压模具费计算完成：2026年，芜湖，T13J，写入 48 件，跳过 40 件"
    )
