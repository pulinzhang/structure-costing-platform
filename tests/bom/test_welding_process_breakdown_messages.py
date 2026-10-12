from app.services.bom.welding_process_breakdown.generate.messages import (
    format_bom_scope,
    format_cleared,
    format_finished,
    format_leaf_without_weld,
    format_scope,
)


def test_breakdown_copy_is_plain_chinese() -> None:
    scope = format_scope("芜湖", "T13J", "D/09", "奇瑞公司")
    bom = format_bom_scope(357, 89)
    leaf = format_leaf_without_weld(8)
    cleared = format_cleared(0)
    finished = format_finished(89, 126)
    text = f"{scope}\n{bom}\n{leaf or ''}\n{cleared}\n{finished}"

    assert scope == "这次拆的是：芜湖，T13J，版本 D/09，顾客 奇瑞公司。"
    assert "写了焊接信息" in bom
    assert leaf is not None
    assert "这次不拆" in leaf
    assert "补上焊接信息" in leaf
    assert "毛坯" not in text
    assert "snapshot" not in text
    assert "L0" not in text
    assert "rollup" not in text
    assert "主表" not in text
    assert format_leaf_without_weld(0) is None
    assert format_cleared(3) == "已清掉上次没审核的拆解 3 个零件，按这次材料清单重新拆。"
    assert finished == "拆完了：89 个零件，126 条焊接工艺。"
