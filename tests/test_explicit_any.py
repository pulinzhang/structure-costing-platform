"""签名和类型声明不得新增显式 Any（回归守卫）。"""

from scripts.check_explicit_any import new_explicit_any


def test_no_new_explicit_any_in_signatures() -> None:
    findings = new_explicit_any()
    assert not findings, "\n".join(findings)
