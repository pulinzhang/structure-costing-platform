"""Router 路径参数回归：注解 int 必须带 :int 转换器。"""

from scripts.check_route_path_params import find_bare_int_path_params


def test_no_bare_int_path_params() -> None:
    violations = find_bare_int_path_params()
    assert not violations, "\n".join(violations)
