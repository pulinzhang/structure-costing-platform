"""BOM 简图锚点：表头列及其左邻（总成 D/E，单件 O/P）。"""

from app.parsers.bom.image_extractor import (
    ASSEMBLY_SKETCH_COL,
    PART_SKETCH_COL,
    sketch_col_family,
)


def test_assembly_header_and_left_neighbor() -> None:
    assert sketch_col_family(ASSEMBLY_SKETCH_COL) == ASSEMBLY_SKETCH_COL
    assert sketch_col_family(ASSEMBLY_SKETCH_COL - 1) == ASSEMBLY_SKETCH_COL


def test_part_header_and_left_neighbor() -> None:
    assert sketch_col_family(PART_SKETCH_COL) == PART_SKETCH_COL
    assert sketch_col_family(PART_SKETCH_COL - 1) == PART_SKETCH_COL


def test_other_columns_are_not_sketches() -> None:
    assert sketch_col_family(0) is None
    assert sketch_col_family(5) is None
    assert sketch_col_family(13) is None
