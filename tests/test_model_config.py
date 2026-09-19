"""Pydantic model_config 必须为 ConfigDict（回归守卫）。"""

from scripts.check_model_config import find_model_config_violations


def test_model_config_is_config_dict() -> None:
    violations = find_model_config_violations()
    assert not violations, "\n".join(violations)
