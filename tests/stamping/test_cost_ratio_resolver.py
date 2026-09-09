"""新增工序默认费用比例：级进模 ×0.80，一出二/双槽/合并再 ÷2。"""

from decimal import Decimal

from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.services.stamping.upload.cost_ratio_preserver import ProcessCostRatioPreserver
from app.services.stamping.upload.cost_ratio_resolver import (
    is_blanking_first_process_code,
    is_prg_process_code,
    is_shared_die_row,
    later_ops_are_blank,
    later_ops_have_shared_die,
    resolve_cost_ratio,
    resolve_new_process_cost_ratio,
    shared_die_labels,
)


def test_progressive_die_only_is_0_80() -> None:
    assert resolve_cost_ratio("级进模", None) == Decimal("0.80")
    assert resolve_cost_ratio("级进模", "单件") == Decimal("0.80")


def test_one_out_of_two_only_is_0_50() -> None:
    assert resolve_cost_ratio(None, "一出二") == Decimal("0.50")


def test_progressive_die_and_one_out_of_two_is_0_40() -> None:
    assert resolve_cost_ratio("级进模", "一出二") == Decimal("0.40")
    assert resolve_cost_ratio("级进", "合并") == Decimal("0.40")


def test_jinjin_blanking_is_not_part_level_progressive() -> None:
    assert resolve_cost_ratio("级进落料", "一出一") == Decimal("1.00")
    assert resolve_cost_ratio("级进落料", "单干") == Decimal("1.00")


def test_jinjin_blanking_multi_process_first_is_0_80() -> None:
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="单干",
        process_code="BL+PI",
        is_first_process=True,
        process_count=2,
        first_process_code="BL+PI",
    ) == Decimal("0.80")
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="单干",
        process_code="FO/RST+FL/PI/PI+CPI",
        is_first_process=False,
        process_count=2,
        first_process_code="BL+PI",
    ) == Decimal("1.00")


def test_shared_die_keywords_still_halve() -> None:
    assert resolve_cost_ratio(None, "双槽") == Decimal("0.50")
    assert resolve_cost_ratio(None, "左右合并") == Decimal("0.50")
    assert resolve_cost_ratio("级进模", "双槽") == Decimal("0.40")


def test_prg_code_with_merge_hand_line_is_0_40() -> None:
    assert resolve_cost_ratio("手工线", "合并", process_code="PRG") == Decimal("0.40")
    assert resolve_cost_ratio(
        "手工线",
        "合并",
        process_code="合并",
        previous_automation="手工线",
        previous_first_process_code="PRG",
    ) == Decimal("0.40")


def test_mate_code_inherits_previous_progressive_is_0_40() -> None:
    assert resolve_cost_ratio(
        "手工线",
        "合并",
        process_code="合并",
        previous_automation="级进模",
    ) == Decimal("0.40")


def test_shared_left_code_does_not_inherit_previous_progressive() -> None:
    assert resolve_cost_ratio(
        "手工线",
        "双槽",
        process_code="FO",
        previous_automation="级进",
    ) == Decimal("0.50")
    assert resolve_cost_ratio(
        "手工",
        "一出二",
        process_code="BL+PI",
        previous_automation="级进",
    ) == Decimal("0.50")


def test_non_shared_does_not_inherit_previous_progressive() -> None:
    assert resolve_cost_ratio(
        "手工线",
        "一出一",
        process_code="FO",
        previous_automation="级进模",
    ) == Decimal("1.00")


def test_later_ops_blank_and_full_share_markers() -> None:
    assert later_ops_are_blank(["", "  "]) is True
    assert later_ops_are_blank(["FO+FL"]) is False
    assert later_ops_have_shared_die(["FO+FL"]) is False
    assert later_ops_have_shared_die(["双槽"]) is True
    assert later_ops_have_shared_die(["一出二"]) is False


def test_blanking_first_codes() -> None:
    assert is_blanking_first_process_code("BL") is True
    assert is_blanking_first_process_code("BL+PI") is True
    assert is_blanking_first_process_code("BL+PI(共用)") is True
    assert is_blanking_first_process_code("共用") is True
    assert is_blanking_first_process_code("DR") is False
    assert is_blanking_first_process_code("双槽") is False
    assert is_blanking_first_process_code("FO") is False


def test_prg_codes() -> None:
    assert is_prg_process_code("PRG-BL+PI") is True
    assert is_prg_process_code("PRG-BL") is True
    assert is_prg_process_code("BL+PI-PRG") is True
    assert is_prg_process_code("PRG") is True
    assert is_prg_process_code("PRG（一出二）") is True
    assert is_prg_process_code("FO") is False


def test_multi_process_first_prg_is_standalone_0_80() -> None:
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出一",
        process_code="PRG-BL+PI",
        is_first_process=True,
        process_count=6,
        first_process_code="PRG-BL+PI",
    ) == Decimal("0.80")
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出一",
        process_code="PRG",
        is_first_process=True,
        process_count=6,
        first_process_code="PRG",
    ) == Decimal("0.80")


def test_multi_process_later_shared_code_is_0_50() -> None:
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出一",
        process_code="双槽",
        is_first_process=False,
        process_count=6,
        first_process_code="PRG-BL+PI",
    ) == Decimal("0.50")


def test_multi_process_later_without_shared_code_is_1_00() -> None:
    assert resolve_new_process_cost_ratio(
        automation="级进",
        process_method="一出一",
        process_code="FL",
        is_first_process=False,
        process_count=4,
        first_process_code="BL+PI-PRG",
    ) == Decimal("1.00")
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出一",
        process_code="FO",
        is_first_process=False,
        process_count=6,
        first_process_code="PRG-BL+PI",
    ) == Decimal("1.00")


def test_multi_process_later_one_out_of_two_is_1_00() -> None:
    assert resolve_new_process_cost_ratio(
        automation="级进",
        process_method="一出二",
        process_code="FO+FL",
        is_first_process=False,
        process_count=5,
        first_process_code="BL+PI-PRG",
    ) == Decimal("1.00")
    assert resolve_new_process_cost_ratio(
        automation="手工",
        process_method="一出二",
        process_code="FO+FL",
        is_first_process=False,
        process_count=4,
        first_process_code="BL+PI",
    ) == Decimal("1.00")
    assert resolve_new_process_cost_ratio(
        automation="手工",
        process_method="一出二",
        process_code="BL+PI",
        is_first_process=True,
        process_count=4,
        first_process_code="BL+PI",
    ) == Decimal("0.50")


def test_later_ops_shared_makes_fo_and_blank_0_50() -> None:
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出一",
        process_code="PRG-BL+PI",
        is_first_process=True,
        process_count=6,
        first_process_code="PRG-BL+PI",
        later_ops_are_shared=True,
    ) == Decimal("0.80")
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出一",
        process_code="FO",
        is_first_process=False,
        process_count=6,
        first_process_code="PRG-BL+PI",
        later_ops_are_shared=True,
    ) == Decimal("0.50")
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出一",
        process_code="",
        is_first_process=False,
        process_count=6,
        first_process_code="PRG-BL+PI",
        later_ops_are_shared=True,
    ) == Decimal("0.50")


def test_shared_first_after_prg_is_0_80_not_1_00() -> None:
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出一",
        process_code="共用",
        is_first_process=True,
        process_count=5,
        first_process_code="共用",
        previous_first_process_code="PRG-BL+PI",
    ) == Decimal("0.80")


def test_shared_first_after_prg_ignores_part_level_half() -> None:
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出二",
        process_code="共用",
        is_first_process=True,
        process_count=6,
        first_process_code="共用",
        previous_first_process_code="PRG-BL",
    ) == Decimal("0.80")
    assert resolve_new_process_cost_ratio(
        automation="级进落料",
        process_method="一出二",
        process_code="双槽",
        is_first_process=False,
        process_count=6,
        first_process_code="共用",
        previous_first_process_code="PRG-BL",
    ) == Decimal("0.50")


def test_double_cavity_blanking_first_is_1_00_later_0_50() -> None:
    assert resolve_new_process_cost_ratio(
        automation="手工线",
        process_method="双槽",
        process_code="BL",
        is_first_process=True,
        process_count=5,
        first_process_code="BL",
    ) == Decimal("1.00")
    assert resolve_new_process_cost_ratio(
        automation="手工线",
        process_method="双槽",
        process_code="FO",
        is_first_process=False,
        process_count=5,
        first_process_code="BL",
    ) == Decimal("0.50")
    assert resolve_new_process_cost_ratio(
        automation="手工线",
        process_method="双槽",
        process_code="共用",
        is_first_process=True,
        process_count=5,
        first_process_code="共用",
    ) == Decimal("1.00")
    assert resolve_new_process_cost_ratio(
        automation="手工线",
        process_method="共用/双槽",
        process_code="BL+PI(共用)",
        is_first_process=True,
        process_count=4,
        first_process_code="BL+PI(共用)",
    ) == Decimal("1.00")
    assert resolve_new_process_cost_ratio(
        automation="手工线",
        process_method="共用/双槽",
        process_code="左右双槽",
        is_first_process=False,
        process_count=4,
        first_process_code="BL+PI(共用)",
    ) == Decimal("0.50")


def test_double_cavity_drawing_first_stays_0_50() -> None:
    assert resolve_new_process_cost_ratio(
        automation="手工线",
        process_method="双槽",
        process_code="DR",
        is_first_process=True,
        process_count=6,
        first_process_code="DR",
    ) == Decimal("0.50")
    assert resolve_new_process_cost_ratio(
        automation="手工线",
        process_method="合并",
        process_code="DR",
        is_first_process=True,
        process_count=5,
        first_process_code="DR",
    ) == Decimal("0.50")


def test_unrelated_first_after_prg_does_not_enter_exception() -> None:
    assert resolve_new_process_cost_ratio(
        automation="手工",
        process_method="一出一",
        process_code="FO",
        is_first_process=True,
        process_count=3,
        first_process_code="FO",
        previous_first_process_code="PRG-BL+PI",
    ) == Decimal("1.00")


def test_single_prg_with_shared_progressive_stays_0_40() -> None:
    assert resolve_new_process_cost_ratio(
        automation="级进模",
        process_method="合并",
        process_code="PRG",
        is_first_process=True,
        process_count=1,
        first_process_code="PRG",
    ) == Decimal("0.40")


def test_preserver_assigns_prg_exception() -> None:
    part = Part(
        part_number="P-LEFT",
        process_method="一出一",
        automation="级进落料",
    )
    first = Process(
        part_number="P-LEFT",
        process_seq="OP05",
        process_code="PRG-BL+PI",
    )
    later = Process(
        part_number="P-LEFT",
        process_seq="OP10",
        process_code="FO",
    )
    shared = Process(
        part_number="P-RIGHT",
        process_seq="OP10",
        process_code="双槽",
    )
    right_first = Process(
        part_number="P-RIGHT",
        process_seq="OP05",
        process_code="PRG-BL+PI",
    )
    right_part = Part(
        part_number="P-RIGHT",
        process_method="一出一",
        automation="级进落料",
    )
    right_empty = Process(
        part_number="P-RIGHT",
        process_seq="OP20",
        process_code="",
    )
    ProcessCostRatioPreserver().apply(
        [first, later, right_first, shared, right_empty],
        [],
        [part, right_part],
    )
    assert first.cost_ratio == Decimal("0.80")
    assert later.cost_ratio == Decimal("0.50")
    assert right_first.cost_ratio == Decimal("0.80")
    assert shared.cost_ratio == Decimal("0.50")
    assert right_empty.cost_ratio == Decimal("0.50")


def test_preserver_merge_hand_line_after_progressive_is_0_40() -> None:
    left = Part(part_number="501042810AA", process_method="合并", automation="级进模")
    right = Part(part_number="501042811AA", process_method="合并", automation="手工线")
    left_op = Process(part_number="501042810AA", process_seq="OP10", process_code="PRG")
    right_op = Process(part_number="501042811AA", process_seq="OP10", process_code="合并")
    ProcessCostRatioPreserver().apply([left_op, right_op], [], [left, right])
    assert left_op.cost_ratio == Decimal("0.40")
    assert right_op.cost_ratio == Decimal("0.40")


def test_preserver_shared_first_follows_previous_prg() -> None:
    left = Part(part_number="HOST", process_method="一出二", automation="级进落料")
    right = Part(part_number="MATE", process_method="一出二", automation="级进落料")
    left_ops = [
        Process(part_number="HOST", process_seq="OP05", process_code="PRG-BL"),
        Process(part_number="HOST", process_seq="OP10", process_code="FO"),
    ]
    right_ops = [
        Process(part_number="MATE", process_seq="OP05", process_code="共用"),
        Process(part_number="MATE", process_seq="OP10", process_code="双槽"),
        Process(part_number="MATE", process_seq="OP20", process_code=""),
    ]
    ProcessCostRatioPreserver().apply(
        [*left_ops, *right_ops],
        [],
        [left, right],
    )
    assert left_ops[0].cost_ratio == Decimal("0.80")
    assert left_ops[1].cost_ratio == Decimal("0.50")
    assert right_ops[0].cost_ratio == Decimal("0.80")
    assert right_ops[1].cost_ratio == Decimal("0.50")
    assert right_ops[2].cost_ratio == Decimal("0.50")


def test_preserver_prg_later_stays_1_00_without_neighbor_shared() -> None:
    part = Part(part_number="SOLO", process_method="一出一", automation="级进落料")
    first = Process(part_number="SOLO", process_seq="OP05", process_code="PRG-BL+PI")
    later = Process(part_number="SOLO", process_seq="OP10", process_code="FO")
    ProcessCostRatioPreserver().apply([first, later], [], [part])
    assert first.cost_ratio == Decimal("0.80")
    assert later.cost_ratio == Decimal("1.00")


def test_preserver_independent_prg_after_shared_pair_later_is_1_00() -> None:
    """T2AA 后围左右连接板之后的独立级进件，后续序不得继承上一对的双槽 0.50。"""
    left = Part(part_number="501029964AA", process_method="一出二", automation="级进落料")
    right = Part(part_number="501029965AA", process_method="一出二", automation="级进落料")
    solo = Part(part_number="501044656AA", process_method="一出一", automation="级进落料")
    left_ops = [
        Process(part_number="501029964AA", process_seq="OP05", process_code="PRG-BL"),
        Process(part_number="501029964AA", process_seq="OP10", process_code="FO"),
    ]
    right_ops = [
        Process(part_number="501029965AA", process_seq="OP05", process_code="共用"),
        Process(part_number="501029965AA", process_seq="OP10", process_code="双槽"),
        Process(part_number="501029965AA", process_seq="OP20", process_code=""),
    ]
    solo_ops = [
        Process(part_number="501044656AA", process_seq="OP05", process_code="PRG-BL"),
        Process(part_number="501044656AA", process_seq="OP10", process_code="FO"),
        Process(part_number="501044656AA", process_seq="OP20", process_code="RST"),
    ]
    ProcessCostRatioPreserver().apply(
        [*left_ops, *right_ops, *solo_ops],
        [],
        [left, right, solo],
    )
    assert left_ops[0].cost_ratio == Decimal("0.80")
    assert left_ops[1].cost_ratio == Decimal("0.50")
    assert right_ops[0].cost_ratio == Decimal("0.80")
    assert right_ops[1].cost_ratio == Decimal("0.50")
    assert solo_ops[0].cost_ratio == Decimal("0.80")
    assert solo_ops[1].cost_ratio == Decimal("1.00")
    assert solo_ops[2].cost_ratio == Decimal("1.00")


def test_preserver_jinjin_merge_pair_is_0_40() -> None:
    left = Part(part_number="502021295AA", process_method="合并", automation="级进")
    right = Part(part_number="502021318AA", process_method="合并", automation="级进")
    left_op = Process(part_number="502021295AA", process_seq="OP10", process_code="PRG")
    right_op = Process(part_number="502021318AA", process_seq="OP10", process_code="合并")
    ProcessCostRatioPreserver().apply([left_op, right_op], [], [left, right])
    assert left_op.cost_ratio == Decimal("0.40")
    assert right_op.cost_ratio == Decimal("0.40")


def test_preserver_gold_t2aa_pairs() -> None:
    """对照工艺确认导出手工核对：后序不叠级进；手工线共模不继承上一件级进。"""
    parts = [
        Part(part_number="501042621AA", process_method="一出二", automation="手工"),
        Part(part_number="501042622AA", process_method="一出二", automation="手工"),
        Part(part_number="501029988AA", process_method="一出一", automation="级进"),
        Part(part_number="502021791AA", process_method="一出二", automation="级进"),
        Part(part_number="502021790AA", process_method="一出二", automation="级进"),
        Part(part_number="502018921AA", process_method="双槽", automation="手工线"),
        Part(part_number="502018922AA", process_method="双槽", automation="手工线"),
        Part(part_number="502027504AA", process_method="合并", automation="手工线"),
        Part(part_number="502027505AA", process_method="合并", automation="手工线"),
    ]
    processes = [
        Process(part_number="501042621AA", process_seq="OP05", process_code="BL+PI"),
        Process(part_number="501042621AA", process_seq="OP10", process_code="FO+FL"),
        Process(part_number="501042622AA", process_seq="OP05", process_code="共用"),
        Process(part_number="501042622AA", process_seq="OP10", process_code="FO+FL"),
        Process(part_number="501029988AA", process_seq="OP05", process_code="BL+PI-PRG"),
        Process(part_number="501029988AA", process_seq="OP10", process_code="FL"),
        Process(part_number="502021791AA", process_seq="OP05", process_code="BL+PI-PRG"),
        Process(part_number="502021791AA", process_seq="OP10", process_code="FO+FL"),
        Process(part_number="502021790AA", process_seq="OP05", process_code="共用"),
        Process(part_number="502021790AA", process_seq="OP10", process_code=""),
        Process(part_number="502018921AA", process_seq="OP10", process_code="FO"),
        Process(part_number="502018922AA", process_seq="OP10", process_code="双槽"),
        Process(part_number="502027504AA", process_seq="OP10", process_code="DR"),
        Process(part_number="502027505AA", process_seq="OP10", process_code="合并"),
    ]
    ProcessCostRatioPreserver().apply(processes, [], parts)
    by_key = {(p.part_number, p.process_seq): p.cost_ratio for p in processes}
    assert by_key[("501042621AA", "OP05")] == Decimal("0.50")
    assert by_key[("501042621AA", "OP10")] == Decimal("1.00")
    assert by_key[("501042622AA", "OP05")] == Decimal("0.50")
    assert by_key[("501042622AA", "OP10")] == Decimal("1.00")
    assert by_key[("501029988AA", "OP05")] == Decimal("0.80")
    assert by_key[("501029988AA", "OP10")] == Decimal("1.00")
    assert by_key[("502021791AA", "OP05")] == Decimal("0.80")
    assert by_key[("502021791AA", "OP10")] == Decimal("0.50")
    assert by_key[("502021790AA", "OP05")] == Decimal("0.80")
    assert by_key[("502021790AA", "OP10")] == Decimal("0.50")
    assert by_key[("502018921AA", "OP10")] == Decimal("0.50")
    assert by_key[("502018922AA", "OP10")] == Decimal("0.50")
    assert by_key[("502027504AA", "OP10")] == Decimal("0.50")
    assert by_key[("502027505AA", "OP10")] == Decimal("0.50")


def test_preserver_haizhong_double_cavity_blanking_pairs() -> None:
    """青岛海众 T28：双槽多序落料第一序 1.00，后序共模 0.50。"""
    parts = [
        Part(part_number="552000656AA", process_method="双槽", automation="手工线"),
        Part(part_number="552000658AA", process_method="双槽", automation="手工线"),
        Part(part_number="502004383AA", process_method="双槽", automation="手工线"),
        Part(part_number="502004419AA", process_method="双槽", automation="手工线"),
        Part(part_number="502006316AA", process_method="共用/双槽", automation="手工线"),
        Part(part_number="502006317AA", process_method="共用/双槽", automation="手工线"),
        Part(part_number="502005521AA", process_method="双槽", automation="手工线"),
        Part(part_number="502005522AA", process_method="双槽", automation="手工线"),
    ]
    processes = [
        Process(part_number="552000656AA", process_seq="OP05", process_code="BL"),
        Process(part_number="552000656AA", process_seq="OP10", process_code="FO"),
        Process(part_number="552000658AA", process_seq="OP05", process_code="共用"),
        Process(part_number="552000658AA", process_seq="OP10", process_code="双槽"),
        Process(part_number="552000658AA", process_seq="OP20", process_code=""),
        Process(part_number="502004383AA", process_seq="OP05", process_code="BL"),
        Process(part_number="502004383AA", process_seq="OP10", process_code="FO"),
        Process(part_number="502004419AA", process_seq="OP05", process_code="共用"),
        Process(part_number="502004419AA", process_seq="OP10", process_code="双槽"),
        Process(part_number="502006316AA", process_seq="OP05", process_code="BL+PI"),
        Process(part_number="502006316AA", process_seq="OP10", process_code="FO"),
        Process(part_number="502006317AA", process_seq="OP05", process_code="BL+PI(共用)"),
        Process(part_number="502006317AA", process_seq="OP10", process_code="左右双槽"),
        Process(part_number="502005521AA", process_seq="OP05", process_code="DR"),
        Process(part_number="502005521AA", process_seq="OP10", process_code="FO"),
        Process(part_number="502005522AA", process_seq="OP05", process_code="双槽"),
        Process(part_number="502005522AA", process_seq="OP10", process_code=""),
    ]
    ProcessCostRatioPreserver().apply(processes, [], parts)
    by_key = {(p.part_number, p.process_seq): p.cost_ratio for p in processes}
    assert by_key[("552000656AA", "OP05")] == Decimal("1.00")
    assert by_key[("552000656AA", "OP10")] == Decimal("0.50")
    assert by_key[("552000658AA", "OP05")] == Decimal("1.00")
    assert by_key[("552000658AA", "OP10")] == Decimal("0.50")
    assert by_key[("552000658AA", "OP20")] == Decimal("0.50")
    assert by_key[("502004383AA", "OP05")] == Decimal("1.00")
    assert by_key[("502004383AA", "OP10")] == Decimal("0.50")
    assert by_key[("502004419AA", "OP05")] == Decimal("1.00")
    assert by_key[("502004419AA", "OP10")] == Decimal("0.50")
    assert by_key[("502006316AA", "OP05")] == Decimal("1.00")
    assert by_key[("502006316AA", "OP10")] == Decimal("0.50")
    assert by_key[("502006317AA", "OP05")] == Decimal("1.00")
    assert by_key[("502006317AA", "OP10")] == Decimal("0.50")
    assert by_key[("502005521AA", "OP05")] == Decimal("0.50")
    assert by_key[("502005521AA", "OP10")] == Decimal("0.50")
    assert by_key[("502005522AA", "OP05")] == Decimal("0.50")
    assert by_key[("502005522AA", "OP10")] == Decimal("0.50")


def test_preserver_haizhong_prg_merge_and_jinjin_blanking() -> None:
    """青岛海众：单序 PRG+合并+手工线 0.40；级进落料第一序 0.80、后序 1.00。"""
    parts = [
        Part(part_number="502005543AA", process_method="合并", automation="手工线"),
        Part(part_number="502005544AA", process_method="合并", automation="手工线"),
        Part(part_number="502005553AA", process_method="单干", automation="级进落料"),
    ]
    processes = [
        Process(part_number="502005543AA", process_seq="OP10", process_code="PRG"),
        Process(part_number="502005544AA", process_seq="OP10", process_code="合并"),
        Process(part_number="502005553AA", process_seq="OP05", process_code="BL+PI"),
        Process(
            part_number="502005553AA",
            process_seq="OP10-OP40",
            process_code="FO/RST+FL/PI/PI+CPI",
        ),
    ]
    ProcessCostRatioPreserver().apply(processes, [], parts)
    by_key = {(p.part_number, p.process_seq): p.cost_ratio for p in processes}
    assert by_key[("502005543AA", "OP10")] == Decimal("0.40")
    assert by_key[("502005544AA", "OP10")] == Decimal("0.40")
    assert by_key[("502005553AA", "OP05")] == Decimal("0.80")
    assert by_key[("502005553AA", "OP10-OP40")] == Decimal("1.00")


def test_shared_die_labels_from_process_method_and_ratio() -> None:
    assert shared_die_labels(
        die_type="铸造模",
        process_method="双槽",
        process_codes=["DR"],
        cost_ratios=[Decimal("0.50")],
    ) == ["双槽"]
    assert is_shared_die_row(
        die_type=None,
        process_method=None,
        process_codes=["合并"],
        cost_ratios=[],
    )
    assert "级进共模" in shared_die_labels(
        die_type=None,
        process_method=None,
        process_codes=[],
        cost_ratios=[Decimal("0.40")],
    )
