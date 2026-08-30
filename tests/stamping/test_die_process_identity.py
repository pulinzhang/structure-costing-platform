import pytest

from app.services.stamping.die.process_identity import (
    ProcessPartIdentity,
    map_die_parts_to_process,
    matches_die_identity,
)


def test_map_die_parts_unique_identity() -> None:
    mapping = map_die_parts_to_process(
        ["50200111aa"],
        [
            ProcessPartIdentity(
                part_number="50200111AA",
                stamping_supplier="安庆常庆",
                version="V1",
            )
        ],
    )
    identity = mapping["50200111AA"]
    assert identity.stamping_supplier == "安庆常庆"
    assert identity.version == "V1"


def test_map_die_parts_missing_raises() -> None:
    with pytest.raises(ValueError, match="工艺中不存在"):
        map_die_parts_to_process(
            ["50200999AA"],
            [
                ProcessPartIdentity(
                    part_number="50200111AA",
                    stamping_supplier="安庆常庆",
                    version="V1",
                )
            ],
        )


def test_map_die_parts_ambiguous_raises() -> None:
    with pytest.raises(ValueError, match="多个供应商或版本"):
        map_die_parts_to_process(
            ["50200111AA"],
            [
                ProcessPartIdentity(
                    part_number="50200111AA",
                    stamping_supplier="安庆常庆",
                    version="V1",
                ),
                ProcessPartIdentity(
                    part_number="50200111AA",
                    stamping_supplier="芜湖",
                    version="V2",
                ),
            ],
        )


def test_map_die_parts_empty_supplier_is_missing() -> None:
    with pytest.raises(ValueError, match="工艺中不存在"):
        map_die_parts_to_process(
            ["50200111AA"],
            [
                ProcessPartIdentity(
                    part_number="50200111AA",
                    stamping_supplier="",
                    version="V1",
                )
            ],
        )


def test_matches_die_identity_optional_filters() -> None:
    assert matches_die_identity("安庆常庆", "V1", stamping_supplier=None, version=None)
    assert matches_die_identity("安庆常庆", "V1", stamping_supplier="安庆常庆", version=None)
    assert matches_die_identity("安庆常庆", "V1", stamping_supplier="安庆常庆", version="V1")
    assert not matches_die_identity("安庆常庆", "V1", stamping_supplier="芜湖", version=None)
    assert not matches_die_identity("安庆常庆", "V1", stamping_supplier=None, version="V2")
