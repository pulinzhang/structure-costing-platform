"""工艺上传：普通件零件名称、材质、料厚不得为空。"""

from decimal import Decimal

from app.exceptions.base import BusinessException
from app.parsers.stamping.models.part import Part
from app.services.stamping.part.upload.gates.validate import require_ordinary_part_fields


def _part(
    part_number: str | None,
    *,
    part_name: str | None = "支架",
    material: str | None = "DC04",
    thickness: Decimal | None = Decimal("1.2"),
    excel_row: int | None = 8,
) -> Part:
    return Part(
        part_number=part_number,
        part_name=part_name,
        material=material,
        thickness=thickness,
        excel_row=excel_row,
    )


def test_filled_ordinary_part_passes() -> None:
    require_ordinary_part_fields([_part("501006875AA")], tailor_parent_numbers=set())


def test_empty_name_material_and_thickness_are_rejected() -> None:
    try:
        require_ordinary_part_fields(
            [
                _part(
                    "501006875AA",
                    part_name="  ",
                    material=None,
                    thickness=None,
                    excel_row=12,
                )
            ],
            tailor_parent_numbers=set(),
        )
    except BusinessException as exc:
        message = str(exc)
        assert "整本未导入" in message
        assert "第 12 行" in message
        assert "501006875AA" in message
        assert "零件名称、材质、料厚是空的" in message
        return
    raise AssertionError("expected BusinessException")


def test_tailor_weld_parent_may_omit_thickness() -> None:
    require_ordinary_part_fields(
        [_part("551001690AA", thickness=None, excel_row=34)],
        tailor_parent_numbers={"551001690AA"},
    )


def test_only_blank_ordinary_rows_are_listed() -> None:
    try:
        require_ordinary_part_fields(
            [
                _part("A", excel_row=8),
                _part("B", material="", excel_row=16),
            ],
            tailor_parent_numbers=set(),
        )
    except BusinessException as exc:
        message = str(exc)
        assert "零件 B" in message
        assert "材质是空的" in message
        assert "零件 A" not in message
        return
    raise AssertionError("expected BusinessException")


def test_row_without_part_number_is_skipped() -> None:
    require_ordinary_part_fields(
        [_part(None, part_name=None, material=None, thickness=None)],
        tailor_parent_numbers=set(),
    )
