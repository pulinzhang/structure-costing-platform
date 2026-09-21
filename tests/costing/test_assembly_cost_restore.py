"""总成核价成本还原报告。"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.routers.costing.assembly_cost import crud
from app.schemas.vo.assembly_cost_restore_vo import RestoreDocumentRefVO
from app.services.costing.assembly_cost.codes import PURCHASED_ASSEMBLY_NOTE
from app.services.costing.assembly_cost.restore.labels import indirect_kind
from app.services.costing.assembly_cost.restore.service import (
    AssemblyCostRestoreService,
)


def _item(**kwargs):
    payload = {
        "id": 1,
        "sort_no": 1,
        "node_level": 1,
        "bom_node_id": 20,
        "part_number": "501000011AA",
        "part_name": "叶子",
        "node_role": None,
        "supply_type": None,
        "cost_source": "stamping",
        "match_hint": None,
        "unit_price": Decimal("2.0000"),
        "effective_qty": Decimal("1"),
        "line_amount": Decimal("2.0000"),
    }
    payload.update(kwargs)
    return SimpleNamespace(**payload)


def _indirect(**kwargs):
    payload = {
        "id": 1,
        "sort_no": 1,
        "code": "unit_transport_fee",
        "label": "单件运输费",
        "amount": Decimal("0"),
        "rate": None,
        "base_amount": None,
    }
    payload.update(kwargs)
    return SimpleNamespace(**payload)


def _card(**kwargs):
    payload = {
        "id": 8,
        "year": 2026,
        "month": 7,
        "location": "芜湖基地",
        "vehicle_model": "T1",
        "bom_version": "A",
        "source_node_id": 10,
        "level": 0,
        "is_tree_root": True,
        "object_kind": "l0_degenerate",
        "part_number": "501006873AA",
        "part_name": "横梁总成",
        "supply_qty": Decimal("1"),
        "bom_snapshot_id": None,
        "root_part_number": "501006873AA",
        "stamping_amount": Decimal("2.0000"),
        "purchased_amount": Decimal("0"),
        "bundle_amount": Decimal("3.0000"),
        "material_amount": Decimal("5.0000"),
        "welding_amount": Decimal("0"),
        "welding_other_fee": Decimal("0"),
        "total_amount": Decimal("5.0000"),
        "should_cost": Decimal("5.0000"),
        "vendor_quote": None,
        "gap_amount": None,
        "vendor_name": None,
        "indirect_amount": Decimal("0.1000"),
        "grand_total": Decimal("5.1000"),
        "calc_status": "ok",
        "audit_status": "pending",
        "formula_version": "assembly-v1",
        "calculated_at": None,
        "calc_batch_id": "b1",
        "welding_fee_id": None,
        "items": [],
        "indirects": [],
    }
    payload.update(kwargs)
    return SimpleNamespace(**payload)


def _bind(service: AssemblyCostRestoreService) -> None:
    service.node_repo.list_by_snapshot = MagicMock(return_value=[])
    service.stamping_repo.list_success_by_part_numbers = MagicMock(return_value=[])
    service.annual_repo.list_by_location_year = MagicMock(return_value=[])
    service.welding_repo.get_by_id = MagicMock(return_value=None)
    service.process_fee_repo.list_by_ids = MagicMock(return_value=[])
    service.die_fee_repo.list_by_ids = MagicMock(return_value=[])
    service.gauge_fee_repo.list_by_ids = MagicMock(return_value=[])
    service.steel_repo.list_by_ids = MagicMock(return_value=[])
    service.scrap_repo.list_by_ids = MagicMock(return_value=[])
    service.base_price_repo.list_by_ids = MagicMock(return_value=[])
    service.packaging_repo.list_by_location_year = MagicMock(return_value=[])
    service.upload_file_repo.list_active_by_scope = MagicMock(return_value=[])
    service.settings_service.get_config = MagicMock(return_value=SimpleNamespace(company_name=""))


def test_restore_route_before_detail() -> None:
    paths = [getattr(route, "path", "") for route in crud.router.routes]
    restore_at = paths.index("/api/costing/assembly-costs/restore")
    by_id_at = paths.index("/api/costing/assembly-costs/{cost_id}/restore")
    detail_at = paths.index("/api/costing/assembly-costs/{cost_id}")
    assert restore_at < by_id_at < detail_at


def test_restore_identity_short_codes_and_skipped() -> None:
    service = AssemblyCostRestoreService()
    _bind(service)
    items = [
        _item(id=1, sort_no=1, cost_source="stamping", line_amount=Decimal("2.0000")),
        _item(
            id=2,
            sort_no=2,
            bom_node_id=21,
            part_number="501000022AA",
            cost_source="bundle",
            unit_price=Decimal("3.0000"),
            line_amount=Decimal("3.0000"),
        ),
        _item(
            id=3,
            sort_no=3,
            bom_node_id=22,
            node_level=2,
            part_number="FQ371B06F36",
            part_name="焊接方螺母",
            cost_source="skipped_by_bundle",
            match_hint="bundle_parent:501000022AA",
            unit_price=Decimal("0"),
            line_amount=Decimal("0"),
        ),
        _item(
            id=4,
            sort_no=4,
            bom_node_id=23,
            part_number="551001730AA",
            cost_source="missing",
            match_hint="multi_supplier_unit_cost",
            unit_price=Decimal("0"),
            line_amount=Decimal("0"),
        ),
    ]
    indirects = [
        _indirect(id=1, sort_no=1, code="unit_transport_fee", amount=Decimal("0.1000")),
        _indirect(
            id=2,
            sort_no=3,
            code="finished_finance_fee",
            label="财务费",
            amount=Decimal("0"),
            rate=Decimal("0.02"),
            base_amount=Decimal("5.0000"),
        ),
    ]
    card = _card(items=items, indirects=indirects)
    service.cost_repo.get_by_id = MagicMock(return_value=card)
    vo = service.get_restore(MagicMock(), 8, view="finance")
    assert vo.short_code == "6873"
    assert vo.highlight_label == "总成价"
    assert vo.highlight_amount == Decimal("5.1000")
    by_code = {row.code: row for row in vo.identity_checks}
    assert by_code["material"].is_match
    assert by_code["grand"].is_match
    skipped = next(node for node in vo.material_nodes if node.cost_source == "skipped_by_bundle")
    assert skipped.line_amount == Decimal("0.0000")
    assert skipped.short_code == "FQ371B06F36"
    missing = next(node for node in vo.material_nodes if node.cost_source == "missing")
    assert missing.short_code == "1730"
    assert any(row.kind == "missing" for row in vo.exceptions)
    assert any("当时的材料清单找不到了" in row.message for row in vo.exceptions)
    kinds = {row.code: row.kind for row in vo.indirects}
    assert kinds["unit_transport_fee"] == "direct"
    assert kinds["finished_finance_fee"] == "allocation"
    assert vo.welding.has_record is False
    assert vo.welding.message == "没有焊接"
    assert not any(
        "工艺费" in (row.message or "") and "断链" in row.message for row in vo.exceptions
    )


def test_restore_purchased_assembly_says_annual_includes_welding() -> None:
    service = AssemblyCostRestoreService()
    _bind(service)
    items = [
        _item(
            id=1,
            sort_no=1,
            bom_node_id=10,
            part_number="502003968AA",
            part_name="左前安全带滑轨上固定板总成",
            cost_source="bundle",
            unit_price=Decimal("6.8800"),
            line_amount=Decimal("6.8800"),
        ),
        _item(
            id=2,
            sort_no=2,
            bom_node_id=11,
            node_level=2,
            part_number="502003966AA",
            part_name="左前安全带滑轨固定板",
            cost_source="skipped_by_bundle",
            match_hint="bundle_parent:502003968AA",
            unit_price=Decimal("0"),
            line_amount=Decimal("0"),
        ),
    ]
    card = _card(
        source_node_id=10,
        part_number="502003968AA",
        part_name="左前安全带滑轨上固定板总成",
        stamping_amount=Decimal("0"),
        purchased_amount=Decimal("0"),
        bundle_amount=Decimal("6.8800"),
        material_amount=Decimal("6.8800"),
        total_amount=Decimal("6.8800"),
        should_cost=Decimal("6.8800"),
        indirect_amount=Decimal("0"),
        grand_total=Decimal("6.8800"),
        items=items,
        indirects=[],
    )
    service.cost_repo.get_by_id = MagicMock(return_value=card)
    vo = service.get_restore(MagicMock(), 8, view="procurement")
    assert vo.is_purchased_assembly is True
    assert vo.welding.has_record is False
    assert vo.welding.message == PURCHASED_ASSEMBLY_NOTE
    skipped = next(node for node in vo.material_nodes if node.cost_source == "skipped_by_bundle")
    assert skipped.cost_source_label == "已含在外购件"


def test_restore_procurement_highlight_and_title_fields() -> None:
    service = AssemblyCostRestoreService()
    _bind(service)
    card = _card(
        items=[],
        indirects=[],
        created_by="系统导入",
        updated_by="张三",
        calculated_at=datetime(2026, 1, 15, 14, 32),
        should_cost=Decimal("9.0000"),
        total_amount=Decimal("5.0000"),
    )
    service.cost_repo.get_by_id = MagicMock(return_value=card)
    vo = service.get_restore(MagicMock(), 8, view="procurement")
    assert vo.view == "procurement"
    assert vo.highlight_label == "结算价"
    assert vo.highlight_amount == Decimal("5.0000")
    assert vo.part_number == "501006873AA"
    assert vo.year == 2026
    assert vo.month == 7
    assert vo.calculated_by == "张三"
    assert vo.calculated_at == datetime(2026, 1, 15, 14, 32)


def test_indirect_kind_split() -> None:
    assert indirect_kind("unit_transport_fee") == "direct"
    assert indirect_kind("warehouse_bundling_fee") == "direct"
    assert indirect_kind("finished_finance_fee") == "allocation"
    assert indirect_kind("gauge_alloc_fee") == "allocation"


def test_restore_missing_card() -> None:
    service = AssemblyCostRestoreService()
    service.cost_repo.get_by_id = MagicMock(return_value=None)
    try:
        service.get_restore(MagicMock(), 99)
        raise AssertionError("expected NotFoundException")
    except Exception as exc:
        assert "不存在" in str(exc)


def test_base_price_excel_from_base_price_row() -> None:
    service = AssemblyCostRestoreService()
    picked = SimpleNamespace(
        steel_price_id=9,
        steel_mill="马钢",
        steel_ton_price=Decimal("4500"),
    )
    steel = SimpleNamespace(
        steel_mill="马钢",
        base_price=Decimal("4300"),
        thickness_adjustment=Decimal("0"),
        width_adjustment=Decimal("0"),
        zinc_adjustment=Decimal("0"),
        processing_fee=Decimal("120"),
        other_adjustment=Decimal("0"),
        final_price_per_ton=Decimal("4420"),
        base_price_id=3,
        base_excel_filename=None,
        base_excel_row=None,
        thickness_excel_filename="马钢厚度加减价.xlsx",
        thickness_excel_row=8,
    )
    base = SimpleNamespace(excel_filename="外协钢板2026年07月.xlsx", excel_row=12)
    vo = service._build_steel(
        picked,
        {9: steel},
        {3: base},
        [],
        "6873",
        "501006873AA",
    )
    assert vo.base_excel_filename == "外协钢板2026年07月.xlsx"
    assert vo.base_excel_row == 12
    assert vo.thickness_excel_filename == "马钢厚度加减价.xlsx"
    assert vo.thickness_excel_row == 8


def test_restore_by_part_unique() -> None:
    service = AssemblyCostRestoreService()
    _bind(service)
    card = _card()
    service.cost_repo.list_by_part_scope = MagicMock(return_value=[card])
    service.cost_repo.get_by_id = MagicMock(return_value=card)
    vo = service.get_restore_by_part(
        MagicMock(),
        year=2026,
        month=7,
        part_number="501006873AA",
    )
    assert vo.part_number == "501006873AA"


def test_restore_by_part_finance_picks_tree_root() -> None:
    service = AssemblyCostRestoreService()
    _bind(service)
    root = _card(id=1, is_tree_root=True)
    child = _card(id=2, is_tree_root=False, procurement_object_id=9)
    service.cost_repo.list_by_part_scope = MagicMock(return_value=[root, child])
    service.cost_repo.get_by_id = MagicMock(return_value=root)
    vo = service.get_restore_by_part(
        MagicMock(),
        year=2026,
        month=7,
        part_number="501006873AA",
        view="finance",
    )
    assert vo.id == 1


def test_restore_by_part_ambiguous_picks_first() -> None:
    service = AssemblyCostRestoreService()
    _bind(service)
    first = _card(id=1, location="芜湖基地", is_tree_root=True)
    second = _card(id=2, location="大连基地", is_tree_root=True)
    service.cost_repo.list_by_part_scope = MagicMock(return_value=[first, second])
    service.cost_repo.get_by_id = MagicMock(return_value=first)
    vo = service.get_restore_by_part(
        MagicMock(),
        year=2026,
        month=7,
        part_number="501006873AA",
    )
    assert vo.id == 1


def test_restore_inserts_sub_assembly_from_snapshot() -> None:
    service = AssemblyCostRestoreService()
    _bind(service)
    items = [
        _item(
            id=1,
            sort_no=1,
            bom_node_id=20,
            node_level=2,
            part_number="502007778AA",
            part_name="滑轨固定板",
            cost_source="stamping",
            unit_price=Decimal("11.5000"),
            line_amount=Decimal("11.5000"),
        ),
    ]
    card = _card(bom_snapshot_id=1, items=items)
    root = SimpleNamespace(
        id=10,
        parent_id=None,
        part_number="501006873AA",
        part_name="横梁总成",
        level=0,
        sort_no=1,
        qty=Decimal("1"),
        node_role=None,
        seq_no=22,
    )
    assembly = SimpleNamespace(
        id=15,
        parent_id=10,
        part_number="502015931AA",
        part_name="前安全带滑轨上固定板总成",
        level=1,
        sort_no=1,
        qty=Decimal("1"),
        node_role=None,
        seq_no=None,
    )
    leaf = SimpleNamespace(
        id=20,
        parent_id=15,
        part_number="502007778AA",
        part_name="滑轨固定板",
        level=2,
        sort_no=1,
        qty=Decimal("1"),
        node_role=None,
        seq_no=None,
    )
    service.node_repo.list_by_snapshot = MagicMock(return_value=[root, assembly, leaf])
    service.cost_repo.get_by_id = MagicMock(return_value=card)
    vo = service.get_restore(MagicMock(), 8, view="finance")
    assert [node.cost_source for node in vo.material_nodes] == ["sub_assembly", "stamping"]
    parent = vo.material_nodes[0]
    assert parent.part_number == "502015931AA"
    assert parent.line_amount == Decimal("11.5000")
    assert parent.unit_price == Decimal("11.5000")
    assert parent.indent_level == 0
    assert parent.seq_label == "22-1"
    assert vo.material_nodes[1].indent_level == 1
    assert vo.material_nodes[1].part_number == "502007778AA"
    assert vo.material_nodes[1].seq_label == "22-1-1"


def test_process_and_die_ops_show_ratio_and_alloc() -> None:
    service = AssemblyCostRestoreService()
    process_row = SimpleNamespace(
        excel_filename="工艺确认.xlsx",
        process_items=[
            SimpleNamespace(
                process_seq="OP10",
                process_code="左右合并",
                original_tonnage=800,
                resolved_tonnage=800,
                tonnage_source="inherited",
                inherited_from_part_number="502007775AA",
                inherited_from_process_seq="OP10",
                cost_ratio=Decimal("0.50"),
                price_per_stroke=Decimal("0.452"),
                line_fee=Decimal("0.226"),
                basis_text="OP10: 继承上一件502007775AA/OP10 800T 比例0.50 × 单价0.452 = 0.226",
            )
        ],
    )
    die_row = SimpleNamespace(
        excel_filename="模具布点.xlsx",
        die_fee=Decimal("1.2140"),
        adjustment_amount=None,
        unit_price=Decimal("1.0000"),
        allocation_qty=Decimal("10"),
        price_kind="steel_plate",
        items=[
            SimpleNamespace(
                process_seq="OP10",
                process_code="左右合并",
                estimated_weight_t=Decimal("2.4280"),
                alloc_ratio=Decimal("0.50"),
                die_sets=1,
                unit_price=Decimal("1.0000"),
                allocation_qty=Decimal("10"),
                price_kind="steel_plate",
                line_die_fee=Decimal("1.2140"),
                basis_text="2.4280 T × 1.0000 万元/吨 × 0.50 / 10 万台 = 1.2140 元",
            )
        ],
    )
    process_ops = service._process_ops(process_row)
    die_ops = service._die_ops(die_row)
    assert process_ops[0].cost_ratio == Decimal("0.5000")
    assert process_ops[0].price_per_stroke == Decimal("0.4520")
    assert die_ops[0].alloc_ratio == Decimal("0.5000")
    assert die_ops[0].allocation_qty == Decimal("10.0000")
    assert die_ops[0].die_sets == 1
    assert die_ops[0].estimated_weight_t == Decimal("2.4280")


def test_restore_documents_skip_duplicate_process_sheet() -> None:
    service = AssemblyCostRestoreService()
    service.upload_file_repo.list_active_by_scope = MagicMock(
        return_value=[SimpleNamespace(original_filename="芜湖2026冲次单价.xlsx")]
    )
    documents: list = []
    picked = SimpleNamespace(
        id=9,
        unit_cost=Decimal("1"),
        direct_cost=Decimal("1"),
        formula_version="v1",
        is_offal_nested=False,
        offal_source=None,
        material_amount_sheet=Decimal("1"),
        loss_scrap_deduction=Decimal("0"),
        process_scrap_deduction=Decimal("0"),
        material_net_per_part=Decimal("1"),
        blank_weight_kg=None,
        finished_total_kg=None,
        scrap_weight_kg=None,
        density=None,
        material_loss_rate=None,
        scrap_recovery_rate=None,
        sheet_length=None,
        sheet_width=None,
        thickness=None,
        parts_per_sheet=None,
        swing_shear_fee_per_ton=None,
        scrap_price_id=None,
        scrap_ton_price=None,
        process_fee_id=1,
        process_fee_amount=Decimal("0.226"),
        die_fee_id=2,
        die_fee_amount=Decimal("1.214"),
        gauge_fee_id=None,
        gauge_fee_amount=None,
        finished_finance_fee=None,
        finished_management_fee=None,
        finished_warehouse_packaging_fee=None,
        finished_pretax_profit_fee=None,
        excel_filename="T13J项目冲压工艺确认表-全鑫.xlsx",
        excel_row=308,
        steel_price_id=None,
        steel_mill=None,
        steel_ton_price=None,
        stamping_supplier="全鑫",
    )
    process_row = SimpleNamespace(
        excel_filename="T13J项目冲压工艺确认表-全鑫.xlsx",
        location="芜湖",
        year=2026,
        process_items=[],
    )
    die_row = SimpleNamespace(
        excel_filename="副本②T13J项目冲压模具布点工艺清单-2024-01-22.xlsx",
        die_fee=Decimal("1.2140"),
        adjustment_amount=None,
        unit_price=Decimal("1"),
        allocation_qty=Decimal("10"),
        price_kind="steel_plate",
        items=[],
    )
    service._build_stamping(
        db=MagicMock(),
        item=_item(part_number="502007795AA"),
        short="7795",
        rows=[picked],
        process_map={1: process_row},
        die_map={2: die_row},
        gauge_map={},
        steel_map={},
        base_price_map={},
        scrap_map={},
        exceptions=[],
        documents=documents,
    )
    names = [(doc.filename, doc.excel_row, doc.file_category_label) for doc in documents]
    assert (
        "T13J项目冲压工艺确认表-全鑫.xlsx",
        308,
        "冲压工艺",
    ) in names
    assert not any(
        name == "T13J项目冲压工艺确认表-全鑫.xlsx" and row is None for name, row, _ in names
    )
    assert (
        "芜湖2026冲次单价.xlsx",
        None,
        "冲次单价",
    ) in names
    assert any(label == "冲压模具布点" for _, _, label in names)
    base = RestoreDocumentRefVO(
        file_category="steel_base_price",
        file_category_label="钢价基准价",
        filename="25年12月份订单.xlsx",
        excel_row=29,
        cited_short_codes=["7795"],
    )
    assert base.file_category_label == "钢价基准价"
