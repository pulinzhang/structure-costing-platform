"""工程变更三表零件号自洽、采购对象缺根硬停。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.common.engineering_change_gates import (
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    EC_AFTER_PART_NOT_ON_BOM,
    EC_AFTER_ROOT_MISSING,
    EC_BOM_HEADER_VERSION_REQUIRED,
    EC_BOM_PROCESS_VERSION_MISMATCH,
    EC_PROCESS_HEADER_VERSION_REQUIRED,
    EC_PROCESS_NOT_ON_BOM,
    PART_LEVEL_L1,
    require_ec_sheet_versions,
)
from app.exceptions.base import BusinessException
from app.parsers.bom.models import BomParsedNode
from app.parsers.engineering_change.design_change.change_order_parser import ChangeOrderRowParsed
from app.services.bom.bom.change_tree_plant.plant import plant_change_tree
from app.services.engineering_change.design_change.upload.gates.sheet_consistency import (
    validate_workbook_part_numbers,
)
from app.services.engineering_change.design_change.upload.persist.breakdown import persist_breakdown
from app.services.engineering_change.design_change.upload.persist.procurement import (
    persist_procurement,
)


def _node(part_number: str, *, level: int = 1) -> BomParsedNode:
    return BomParsedNode(
        level=level,
        parent_index=None,
        sort_no=1,
        part_number=part_number,
    )


def _order(
    *, after_part: str | None, change_type: str = CHANGE_TYPE_REVISE
) -> ChangeOrderRowParsed:
    return ChangeOrderRowParsed(
        project_code="T28",
        effective_period_text="2025年07月",
        change_type=change_type,
        before_assembly_part_number="A",
        after_assembly_part_number="B",
        assembly_name="总成",
        part_level=PART_LEVEL_L1,
        before_part_number="OLD",
        after_part_number=after_part,
        part_name="件",
        excel_row=5,
    )


def test_workbook_lists_all_missing_numbers_once() -> None:
    with pytest.raises(BusinessException) as caught:
        validate_workbook_part_numbers(
            bom_nodes=[_node("KEEP")],
            process_part_numbers={"P-A", "P-B"},
            change_orders=[
                _order(after_part="NEW-1"),
                _order(after_part="NEW-2"),
            ],
        )
    text = caught.value.message
    assert EC_PROCESS_NOT_ON_BOM in text
    assert "P-A" in text and "P-B" in text
    assert EC_AFTER_PART_NOT_ON_BOM in text
    assert "NEW-1" in text and "NEW-2" in text


def test_empty_after_part_and_empty_process_pass() -> None:
    validate_workbook_part_numbers(
        bom_nodes=[_node("KEEP")],
        process_part_numbers=set(),
        change_orders=[_order(after_part=None, change_type=CHANGE_TYPE_STOP)],
    )


def test_persist_procurement_none_after_root_raises() -> None:
    with pytest.raises(BusinessException, match=EC_AFTER_ROOT_MISSING):
        persist_procurement(
            MagicMock(),
            change_order=_order(after_part="NEW-1"),
            after_root_id=None,
            current_user=MagicMock(),
        )


def test_persist_breakdown_none_after_root_raises() -> None:
    with pytest.raises(BusinessException, match=EC_AFTER_ROOT_MISSING):
        persist_breakdown(
            MagicMock(),
            change_order=_order(after_part="NEW-1"),
            after_root_id=None,
            source_id_remap={},
            current_user=MagicMock(),
        )


def test_aligned_versions_required() -> None:
    assert require_ec_sheet_versions(bom_version="EC-202507", process_version="EC-202507") == (
        "EC-202507"
    )
    with pytest.raises(BusinessException, match=EC_BOM_HEADER_VERSION_REQUIRED):
        require_ec_sheet_versions(bom_version="", process_version="EC-202507")
    with pytest.raises(BusinessException, match=EC_PROCESS_HEADER_VERSION_REQUIRED):
        require_ec_sheet_versions(bom_version="EC-202507", process_version="")
    with pytest.raises(BusinessException, match=EC_BOM_PROCESS_VERSION_MISMATCH):
        require_ec_sheet_versions(bom_version="EC-A", process_version="EC-B")


def test_plant_rejects_empty_bom_version() -> None:
    with pytest.raises(BusinessException, match=EC_BOM_HEADER_VERSION_REQUIRED):
        plant_change_tree(
            MagicMock(),
            MagicMock(),
            snapshot_id=1,
            location="青岛",
            vehicle_model="T28",
            before_l0_id=1,
            seq_no=1,
            spec=MagicMock(),
            parsed_nodes=[],
            effective_year=2025,
            effective_month=7,
            expiry_year=None,
            expiry_month=None,
            current_user=MagicMock(),
            node_bom_version=None,
        )
