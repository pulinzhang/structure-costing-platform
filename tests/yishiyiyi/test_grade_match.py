"""政策牌号与基价/材料牌号互认：斜杠双牌号 vs 双相钢屈服/抗拉写法。"""

from types import SimpleNamespace

from app.services.yishiyiyi.policy.match.adjustment_common import (
    grade_alias_tokens,
    grade_exact,
    grades_match,
)


def test_slash_dual_grade_tokens() -> None:
    assert grade_alias_tokens("B170P1/HC180Y") == frozenset({"B170P1", "HC180Y"})
    assert grade_alias_tokens("B170P1 / HC180Y") == frozenset({"B170P1", "HC180Y"})
    assert grade_alias_tokens("B250P1//HC260Y") == frozenset({"B250P1", "HC260Y"})


def test_dual_phase_grade_stays_atomic() -> None:
    assert grade_alias_tokens("HC340/590DP") == frozenset({"HC340/590DP"})
    assert grade_alias_tokens("HC420/780DPD+Z") == frozenset({"HC420/780DPD+Z"})


def test_grades_match_hc180y_against_magang_dual_name() -> None:
    assert grades_match("B170P1/HC180Y", "HC180Y")
    assert grades_match("HC180Y", "B170P1/HC180Y")
    assert grades_match("B170P1/HC180Y", "B170P1")
    assert grades_match("B170P1/HC180Y", "B170P1/HC180Y")


def test_grades_match_rejects_different_steel() -> None:
    assert not grades_match("B170P1/HC180Y", "DC01")
    assert not grades_match("HC180Y", "HC180YD+Z")
    assert not grades_match("HC340/590DP", "HC340")
    assert not grades_match("HC340/590DP", "HC340LA")
    assert not grades_match("", "HC180Y")
    assert not grades_match("HC180Y", None)


def test_grade_exact_accepts_slash_alias_for_thickness_policy() -> None:
    policy = SimpleNamespace(grade_value="B170P1/HC180Y", grade_type="GRADE")
    row = SimpleNamespace(grade="HC180Y")
    assert grade_exact(policy, row)


def test_grade_exact_rejects_non_grade_type() -> None:
    policy = SimpleNamespace(grade_value="B170P1/HC180Y", grade_type="THICKNESS_RANGE")
    row = SimpleNamespace(grade="HC180Y")
    assert not grade_exact(policy, row)
