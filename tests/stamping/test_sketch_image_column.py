"""冲压工艺简图锚点列：表头列及其左邻（C 起点、D 表头）。"""

from app.parsers.stamping.stamping_parser import allowed_sketch_anchor_cols


def test_default_allows_c_and_d() -> None:
    assert allowed_sketch_anchor_cols(None) == frozenset({2, 3})


def test_header_d_allows_left_neighbor_c() -> None:
    assert allowed_sketch_anchor_cols(4) == frozenset({2, 3})


def test_header_c_allows_b_and_c() -> None:
    assert allowed_sketch_anchor_cols(3) == frozenset({1, 2})


def test_header_a_has_no_left_neighbor() -> None:
    assert allowed_sketch_anchor_cols(1) == frozenset({0})
