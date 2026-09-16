from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeFailedItemVO
from app.services.stamping.process_fee.calc.orchestrator.batch_engine import BatchCalcOutcome
from app.services.stamping.process_fee.calc.orchestrator.messages import (
    append_result_detail,
    format_parts_matched,
    format_prep_opening,
    format_rate_loaded,
)


def test_prep_and_result_copy_is_plain_chinese() -> None:
    assert format_prep_opening(2025, "青岛", "烟台海众汽车零部件有限公司") == (
        "开始计算：2025年，青岛，烟台海众汽车零部件有限公司"
    )
    assert format_rate_loaded(23) == "已加载 23 档冲次单价"
    assert format_parts_matched(116) == "本范围共 116 个有效期内冲压零件"

    batch = BatchCalcOutcome(
        success_count=116,
        zero_fee_count=2,
        scrap_zero_count=2,
        zero_fee_items=[
            StampingProcessFeeFailedItemVO(
                part_number="502018924AA",
                reason="废料副产品，冲压加工费为 0",
            ),
            StampingProcessFeeFailedItemVO(
                part_number="502018925AA",
                reason="废料副产品，冲压加工费为 0",
            ),
        ],
    )
    lines: list[str] = []
    append_result_detail(lines, batch)
    text = "\n".join(lines)
    assert "116 个零件都算完了" in text
    assert "废料副产品" in text
    assert "不用补其它费用" in text
    assert "请到" not in text
    assert "零价" not in text
