"""增加一套一级节点：种树把这一级和它下面至少两颗二级挂上，不往已导入的库再传。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_ADD_SUBASSEMBLY,
    CHANGE_TYPE_NOT_INSTALL,
    NOT_INSTALL_REMARK,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
)
from app.database import Base
from app.models.bom.node import BomNode, BomSnapshot
from app.models.masterdata.location import Location
from app.models.masterdata.vehicle_model import VehicleModel
from app.parsers.bom.bom_parser import parse_bom_excel
from app.parsers.bom.models import BomParsedNode
from app.parsers.engineering_change.design_change.change_order_parser import (
    parse_change_order_sheet,
)
from app.parsers.engineering_change.design_change.sheet_extract import SHEET_BOM
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.change_tree_plant.types import BomChangePlantSpec
from app.services.bom.bom.engineering import BomEngineeringService
from app.services.engineering_change.design_change.upload.gates.bom_slice import (
    slice_bom_nodes_for_l0,
)
from app.services.engineering_change.design_change.upload.gates.tree_gates import (
    validate_change_tree_gates,
)
from app.services.engineering_change.design_change.upload.persist.tree import (
    change_order_to_plant_spec,
)

LOCATION = "青岛"
VEHICLE = "T28"
USER = UserVO(id=1, username="tester", real_name="测试员")
_WORKBOOK = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "engineering-change"
    / "design-change"
    / "设计变更导入_青岛_T28模版 增加二级 一级变更.xlsx"
)
_OLD = "501004437AA"
_SUB = "501004437AA-1"
_ADDED = "501005123AA"
_BEFORE = "501007029AA"
_AFTER = "501007029AB"


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(
        bind=engine,
        tables=[
            Location.__table__,
            VehicleModel.__table__,
            BomSnapshot.__table__,
            BomNode.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    session.add(
        Location(
            location=LOCATION,
            is_enabled=True,
            sort_order=1,
            created_by="system",
            updated_by="system",
        )
    )
    session.add(
        VehicleModel(
            location=LOCATION,
            vehicle_model=VEHICLE,
            effective_year=2020,
            effective_month=1,
            created_by="system",
            updated_by="system",
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _snapshot(db: Session) -> BomSnapshot:
    row = BomSnapshot(
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version="EC-202507",
        stage="initial",
        status="active",
        source_filename="fixture.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.flush()
    return row


def _node(
    db: Session,
    snapshot: BomSnapshot,
    *,
    parent_id: int | None,
    level: int,
    part_number: str,
    sort_no: int = 0,
    internal_number: str | None = None,
    node_role: str = "make",
    sketch_url: str | None = None,
) -> BomNode:
    row = BomNode(
        snapshot_id=snapshot.id,
        parent_id=parent_id,
        level=level,
        sort_no=sort_no,
        part_number=part_number,
        internal_number=internal_number,
        node_role=node_role,
        qty=Decimal("1"),
        sketch_url=sketch_url,
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version=snapshot.bom_version,
        effective_year=2025,
        effective_month=1,
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.flush()
    return row


def test_plant_leaf_demote_hangs_old_number_under_new_subassembly(memory_db: Session) -> None:
    if not _WORKBOOK.is_file():
        pytest.skip("测试本不在本机")
    raw = _WORKBOOK.read_bytes()
    orders = [
        order
        for order in parse_change_order_sheet(raw)
        if order.before_assembly_part_number.strip() == _BEFORE
    ]
    assert [order.change_type for order in orders] == [
        CHANGE_TYPE_NOT_INSTALL,
        CHANGE_TYPE_ADD_PART,
        CHANGE_TYPE_ADD_SUBASSEMBLY,
    ]
    sliced = slice_bom_nodes_for_l0(
        parse_bom_excel(raw, sheet_name=SHEET_BOM).nodes,
        _AFTER,
    )
    snapshot = _snapshot(memory_db)
    root = _node(
        memory_db,
        snapshot,
        parent_id=None,
        level=0,
        part_number=_BEFORE,
        node_role="supply",
        internal_number="ACA614",
    )
    old_leaf = _node(
        memory_db,
        snapshot,
        parent_id=root.id,
        level=1,
        part_number=_OLD,
        sort_no=2,
        internal_number="ACA392002",
        sketch_url="sketches/old-437.png",
    )
    _node(
        memory_db,
        snapshot,
        parent_id=root.id,
        level=1,
        part_number="501007031AA",
        sort_no=1,
    )
    sub = _node(
        memory_db,
        snapshot,
        parent_id=root.id,
        level=1,
        part_number="501005057AA",
        sort_no=3,
        node_role="structure",
        internal_number="ACA057",
    )
    _node(memory_db, snapshot, parent_id=sub.id, level=2, part_number="501007904AA", sort_no=1)
    _node(memory_db, snapshot, parent_id=sub.id, level=2, part_number="501007905AA", sort_no=2)
    old_nodes = BomEngineeringService().list_subtree_nodes(memory_db, root_id=root.id)
    for order in orders:
        validate_change_tree_gates(order, old_nodes, sliced)

    result = BomEngineeringService().plant_change_tree(
        memory_db,
        snapshot_id=snapshot.id,
        location=LOCATION,
        vehicle_model=VEHICLE,
        before_l0_id=root.id,
        seq_no=5,
        spec=change_order_to_plant_spec(orders[0]),
        parsed_nodes=sliced,
        extra_specs=tuple(change_order_to_plant_spec(order) for order in orders[1:]),
        effective_year=2025,
        effective_month=7,
        expiry_year=2028,
        expiry_month=12,
        current_user=USER,
        node_bom_version="EC-202507",
    )
    assert result.not_install_count == 1
    assert result.source_id_remap[old_leaf.id] != old_leaf.id
    planted = BomEngineeringService().list_subtree_nodes(memory_db, root_id=result.new_l0_id)
    by_number = {node.part_number: node for node in planted}
    assert by_number[_AFTER].level == 0
    assert _OLD not in {node.part_number for node in planted if int(node.level) == 1}
    renamed = by_number["501005057AB"]
    assert int(renamed.level) == 1
    assert renamed.parent_id == result.new_l0_id
    assert "501005057AA" not in by_number
    added_under_renamed = next(
        node for node in planted if node.part_number == _OLD and node.parent_id == renamed.id
    )
    assert int(added_under_renamed.level) == 2
    assert added_under_renamed.internal_number == "ACA392002"
    assert added_under_renamed.qty == Decimal("1")
    assert result.source_id_remap[old_leaf.id] == added_under_renamed.id
    subassembly = by_number[_SUB]
    assert int(subassembly.level) == 1
    assert subassembly.parent_id == result.new_l0_id
    assert subassembly.internal_number == "ACA613005"
    under_subassembly = [node for node in planted if node.parent_id == subassembly.id]
    assert {node.part_number for node in under_subassembly} == {_ADDED, _OLD}
    assert by_number["501007031AA"].parent_id == result.new_l0_id
    assert by_number["501007904AA"].parent_id == renamed.id
    assert by_number["501007905AA"].parent_id == renamed.id


def test_classic_not_install_still_omits_the_part(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    root = _node(
        memory_db,
        snapshot,
        parent_id=None,
        level=0,
        part_number="501009144AA",
        node_role="supply",
    )
    _node(memory_db, snapshot, parent_id=root.id, level=1, part_number="501003649AA", sort_no=1)
    _node(memory_db, snapshot, parent_id=root.id, level=1, part_number="501007031AA", sort_no=2)
    parsed = [
        BomParsedNode(level=0, parent_index=None, sort_no=0, part_number="501009144AB"),
        BomParsedNode(
            level=1,
            parent_index=0,
            sort_no=1,
            part_number="501003649AA",
            qty=Decimal("0"),
            remark=NOT_INSTALL_REMARK,
        ),
    ]
    spec = BomChangePlantSpec(
        change_type=CHANGE_TYPE_NOT_INSTALL,
        before_assembly_part_number="501009144AA",
        after_assembly_part_number="501009144AB",
        assembly_name="后防撞梁总成",
        part_level=PART_LEVEL_L1,
        before_part_number="501003649AA",
        after_part_number=None,
        part_name="后防撞梁左安装板",
    )
    result = BomEngineeringService().plant_change_tree(
        memory_db,
        snapshot_id=snapshot.id,
        location=LOCATION,
        vehicle_model=VEHICLE,
        before_l0_id=root.id,
        seq_no=2,
        spec=spec,
        parsed_nodes=parsed,
        effective_year=2025,
        effective_month=7,
        expiry_year=None,
        expiry_month=None,
        current_user=USER,
        node_bom_version="EC-202507",
    )
    planted = BomEngineeringService().list_subtree_nodes(memory_db, root_id=result.new_l0_id)
    numbers = {node.part_number for node in planted}
    assert "501003649AA" not in numbers
    assert "501007031AA" in numbers
    assert result.not_install_count == 1


def test_add_l2_under_existing_children_still_renames_only_that_level1(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    root = _node(
        memory_db,
        snapshot,
        parent_id=None,
        level=0,
        part_number="501007029AA",
        node_role="supply",
    )
    parent = _node(
        memory_db,
        snapshot,
        parent_id=root.id,
        level=1,
        part_number="501004437AA",
        sort_no=2,
        node_role="structure",
    )
    _node(memory_db, snapshot, parent_id=parent.id, level=2, part_number="501007904AA", sort_no=1)
    _node(memory_db, snapshot, parent_id=root.id, level=1, part_number="501007031AA", sort_no=1)
    parsed = [
        BomParsedNode(level=0, parent_index=None, sort_no=0, part_number="501007029AB"),
        BomParsedNode(
            level=1,
            parent_index=0,
            sort_no=2,
            part_number="501004437AB",
            internal_number="ACA613005",
        ),
        BomParsedNode(
            level=2,
            parent_index=1,
            sort_no=1,
            part_number="501005123AA",
            qty=Decimal("1"),
        ),
    ]
    spec = BomChangePlantSpec(
        change_type=CHANGE_TYPE_ADD_PART,
        before_assembly_part_number="501007029AA",
        after_assembly_part_number="501007029AB",
        assembly_name="中通道",
        part_level=PART_LEVEL_L2,
        before_part_number=None,
        after_part_number="501005123AA",
        part_name="新二级",
    )
    result = BomEngineeringService().plant_change_tree(
        memory_db,
        snapshot_id=snapshot.id,
        location=LOCATION,
        vehicle_model=VEHICLE,
        before_l0_id=root.id,
        seq_no=4,
        spec=spec,
        parsed_nodes=parsed,
        effective_year=2025,
        effective_month=7,
        expiry_year=None,
        expiry_month=None,
        current_user=USER,
        node_bom_version="EC-202507",
    )
    planted = BomEngineeringService().list_subtree_nodes(memory_db, root_id=result.new_l0_id)
    by_number = {node.part_number: node for node in planted}
    assert "501004437AA" not in by_number
    renamed = by_number["501004437AB"]
    assert int(renamed.level) == 1
    assert by_number["501005123AA"].parent_id == renamed.id
    assert by_number["501007904AA"].parent_id == renamed.id
    assert by_number["501007031AA"].part_number == "501007031AA"
