"""采购价格 — 只读查询（准备表 + 价目汇总）。

取件：基地 + 项目 + 账期月；问期/浏览先爬 L0（l0_node_of）；禁止 snapshot 定范围。
导出：必须全部版本（bom_version 空）。
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.bom.node_order import bom_node_order_from
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom.node import BomNode
from app.models.bom.procurement_object import BomProcurementObject, BomProcurementObjectList
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.costing.assembly_cost.assembly_cost_repository import (
    AssemblyCostRepository,
    SettlementAmountField,
)
from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.repositories.stamping.gauge_fee.repository import StampingGaugeFeeRepository
from app.schemas.dto.procurement_contract_report_dto import ProcurementContractReportQuery
from app.schemas.vo.procurement_contract_report_vo import (
    ProcurementContractMonthAmountVO,
    ProcurementContractMonthColumnVO,
    ProcurementContractOpenDefaultsVO,
    ProcurementContractReportFiltersVO,
    ProcurementContractReportPrepVO,
    ProcurementContractReportRowVO,
)
from app.services.bom.procurement_object.classify import KIND_L1_STAMPING
from app.services.costing.procurement_contract_report.assemble import (
    VIEW_ASSEMBLY,
    VIEW_PROCUREMENT,
    PrepRow,
    PriceRow,
    ReportBundle,
    ReportScope,
    ToolingAmounts,
    aggregate_price_rows,
    build_assembly_prep_rows,
    build_prep_rows,
    count_missing_month_cells,
    prep_row_order_key,
    report_sort_key,
    resolve_tooling,
    sum_vehicle_total,
)
from app.services.costing.procurement_contract_report.qty import l0_node_of
from app.services.costing.procurement_contract_report.window import expand_months, month_header
from app.services.masterdata.supplier.supplier_service import SupplierService

_SECTION_OBJECT = "object"
_EMPTY_OBJECT_HINT = "当前范围没有采购对象行"
_EMPTY_ASSEMBLY_HINT = "当前范围没有供货总成"
_MISSING_OBJECT_LIST = "请先生成采购对象清单"
_EXPORT_ALL_VERSIONS = "导出协议须选全部版本"


class ProcurementContractReportService:
    def __init__(self) -> None:
        self.object_repo = BomProcurementObjectRepository()
        self.node_repo = BomNodeRepository()
        self.cost_repo = AssemblyCostRepository()
        self.die_fee_repo = StampingDieFeeRepository()
        self.gauge_fee_repo = StampingGaugeFeeRepository()
        self.supplier_service = SupplierService()

    def paginate(
        self,
        db: Session,
        query: ProcurementContractReportQuery,
    ) -> tuple[list[ProcurementContractReportRowVO], int, ProcurementContractReportFiltersVO]:
        bundle = self.build_report(db, query)
        rows = _filter_price_rows(bundle.price_rows, query.keyword)
        vehicle_total, vehicle_total_skipped = sum_vehicle_total(rows, bundle.months)
        total = len(rows)
        start = (query.page - 1) * query.size
        sliced = rows[start : start + query.size]
        filters = _to_filters(bundle, query)
        filters.price_row_count = total
        filters.vehicle_total = vehicle_total
        filters.vehicle_total_skipped = vehicle_total_skipped
        filters.missing_month_cell_count = sum(
            1 for row in rows for cell in row.month_amounts if cell.should_cost is None
        )
        filters.specified_supplier_count = len(
            {name for row in rows for name in row.supplier_names}
        )
        if not rows and query.keyword:
            filters.empty_hint = "没有匹配零件号或名称的价目行"
        return (
            [_to_row_vo(row, _abbreviation_map(self.supplier_service, db)) for row in sliced],
            total,
            filters,
        )

    def prep(
        self,
        db: Session,
        query: ProcurementContractReportQuery,
    ) -> ProcurementContractReportPrepVO:
        bundle = self.build_report(db, query)
        return ProcurementContractReportPrepVO(
            view=bundle.scope.view,
            qa_passed=bundle.scope.qa_passed,
            qa_error_text=bundle.scope.qa_error_text,
            months=_month_columns(bundle.months),
            supplier_names=bundle.supplier_names,
            prep_row_count=len(bundle.prep_rows),
            price_row_count=len(bundle.price_rows),
            specified_supplier_count=len(bundle.supplier_names),
            window_month_count=len(bundle.months),
            missing_month_cell_count=bundle.missing_month_cell_count,
            empty_hint=_empty_hint(bundle),
            vehicle_total=bundle.vehicle_total,
            vehicle_total_skipped=bundle.vehicle_total_skipped,
        )

    def get_open_defaults(self, db: Session) -> ProcurementContractOpenDefaultsVO:
        """打开默认：基地 / 项目 / 年月；版本默认全部（不填）。"""
        latest = self.cost_repo.get_latest_scope_year_month(db)
        if latest is not None:
            location, vehicle_model, _bom_version, year, month = latest
            return ProcurementContractOpenDefaultsVO(
                location=location,
                vehicle_model=vehicle_model,
                bom_version=None,
                start_year=year,
                start_month=month,
                end_year=year,
                end_month=month,
            )
        header = self.object_repo.get_latest_list(db)
        if header is None:
            return ProcurementContractOpenDefaultsVO()
        return ProcurementContractOpenDefaultsVO(
            location=header.location,
            vehicle_model=header.vehicle_model,
            bom_version=None,
        )

    def build_report(
        self,
        db: Session,
        query: ProcurementContractReportQuery,
        *,
        for_export: bool = False,
    ) -> ReportBundle:
        if for_export and query.bom_version:
            raise BusinessException(_EXPORT_ALL_VERSIONS)
        months = expand_months(
            start_year=query.start_year,
            start_month=query.start_month,
            end_year=query.end_year,
            end_month=query.end_month,
        )
        if query.view == VIEW_ASSEMBLY:
            return self._build_assembly_report(db, query, months)
        return self._build_procurement_report(db, query, months)

    def _build_procurement_report(
        self,
        db: Session,
        query: ProcurementContractReportQuery,
        months: list[tuple[int, int]],
    ) -> ReportBundle:
        headers = self.object_repo.list_lists_by_location_vehicle(
            db, location=query.location, vehicle_model=query.vehicle_model
        )
        if not headers:
            raise NotFoundException(_MISSING_OBJECT_LIST)
        supplier_name = self._resolve_supplier(db, query.supplier_name)
        scope_objects = [
            row
            for row in self.object_repo.list_objects_by_location_vehicle(
                db, location=query.location, vehicle_model=query.vehicle_model
            )
            if row.section == _SECTION_OBJECT
        ]
        objects = [
            row for row in scope_objects if not supplier_name or row.supplier_name == supplier_name
        ]
        nodes_by_id = _nodes_by_id(
            self.node_repo.list_by_location_vehicle(
                db, location=query.location, vehicle_model=query.vehicle_model
            )
        )
        objects = _filter_objects_by_climbed_l0_version(objects, nodes_by_id, query.bom_version)
        costs = self._load_costs(
            db,
            query=query,
            months=months,
            source_node_ids=[row.source_node_id for row in objects],
        )
        prep_rows = build_prep_rows(objects, nodes_by_id, months, costs)
        return self._finish_bundle(
            db,
            query=query,
            months=months,
            scope=_scope_from_lists(headers, query),
            prep_rows=prep_rows,
            supplier_name=supplier_name,
        )

    def _build_assembly_report(
        self,
        db: Session,
        query: ProcurementContractReportQuery,
        months: list[tuple[int, int]],
    ) -> ReportBundle:
        nodes = self.node_repo.list_by_location_vehicle(
            db, location=query.location, vehicle_model=query.vehicle_model
        )
        roots = sorted(
            [
                node
                for node in nodes
                if int(node.level) == 0
                and (not query.bom_version or node.bom_version == query.bom_version)
            ],
            key=bom_node_order_from,
        )
        costs = self._load_costs(
            db,
            query=query,
            months=months,
            source_node_ids=[node.id for node in roots],
        )
        prep_rows = build_assembly_prep_rows(roots, months, costs)
        return self._finish_bundle(
            db,
            query=query,
            months=months,
            scope=ReportScope(
                location=query.location,
                vehicle_model=query.vehicle_model,
                bom_version=query.bom_version,
                view=VIEW_ASSEMBLY,
            ),
            prep_rows=prep_rows,
            supplier_name=None,
        )

    def _finish_bundle(
        self,
        db: Session,
        *,
        query: ProcurementContractReportQuery,
        months: list[tuple[int, int]],
        scope: ReportScope,
        prep_rows: list[PrepRow],
        supplier_name: str | None,
    ) -> ReportBundle:
        tooling = self._load_tooling(db, query, prep_rows)
        price_rows = aggregate_price_rows(prep_rows, months, tooling)
        prep_rows.sort(
            key=lambda row: (
                *report_sort_key(scope.location, scope.vehicle_model, row.seq_label),
                *prep_row_order_key(row),
            )
        )
        price_rows.sort(
            key=lambda row: (
                *report_sort_key(scope.location, scope.vehicle_model, row.seq_label),
                row.part_number,
            )
        )
        vehicle_total, vehicle_total_skipped = sum_vehicle_total(price_rows, months)
        suppliers = sorted(
            {name for row in prep_rows if row.supplier_name for name in [row.supplier_name]}
        )
        return ReportBundle(
            scope=scope,
            months=months,
            prep_rows=prep_rows,
            price_rows=price_rows,
            missing_month_cell_count=count_missing_month_cells(prep_rows),
            supplier_names=suppliers,
            supplier_name=supplier_name,
            vehicle_total=vehicle_total,
            vehicle_total_skipped=vehicle_total_skipped,
        )

    def _resolve_supplier(self, db: Session, raw: str | None) -> str | None:
        if not raw:
            return None
        canonical = self.supplier_service.resolve_canonical(db, raw)
        return canonical or raw

    def _load_costs(
        self,
        db: Session,
        *,
        query: ProcurementContractReportQuery,
        months: list[tuple[int, int]],
        source_node_ids: list[int],
    ) -> dict[tuple[int, int, int], Decimal]:
        amount_field: SettlementAmountField = (
            "grand_total" if query.view == VIEW_ASSEMBLY else "total_amount"
        )
        # 读卡不按版本滤；列表浏览筛已在行集合上按爬到的 L0 字裁完
        rows = self.cost_repo.list_should_costs_for_nodes(
            db,
            location=query.location,
            vehicle_model=query.vehicle_model,
            months=months,
            source_node_ids=source_node_ids,
            amount_field=amount_field,
            bom_version=None,
        )
        return {(year, month, node_id): amount for year, month, node_id, amount in rows}

    def _load_tooling(
        self,
        db: Session,
        query: ProcurementContractReportQuery,
        prep_rows: list[PrepRow],
    ) -> dict[str, ToolingAmounts]:
        if not any(row.object_kind == KIND_L1_STAMPING for row in prep_rows):
            return {}
        part_numbers = list(dict.fromkeys(row.part_number for row in prep_rows))
        die_fees = self.die_fee_repo.map_final_die_fee_by_part_numbers(
            db,
            year=query.start_year,
            location=query.location,
            vehicle_model=query.vehicle_model,
            part_numbers=part_numbers,
        )
        gauge_fees = self.gauge_fee_repo.map_effective_by_part_numbers(
            db,
            location=query.location,
            vehicle_model=query.vehicle_model,
            part_numbers=part_numbers,
        )
        by_kind = {row.part_number: row.object_kind for row in prep_rows}
        return {
            part_number: resolve_tooling(
                object_kind=by_kind.get(part_number),
                part_number=part_number,
                die_fees=die_fees,
                gauge_fees=gauge_fees,
            )
            for part_number in part_numbers
        }


def _scope_from_lists(
    headers: list[BomProcurementObjectList],
    query: ProcurementContractReportQuery,
) -> ReportScope:
    qa_passed = all(header.qa_passed for header in headers)
    qa_errors = [header.qa_error_text for header in headers if header.qa_error_text]
    return ReportScope(
        location=query.location,
        vehicle_model=query.vehicle_model,
        bom_version=query.bom_version,
        view=VIEW_PROCUREMENT,
        qa_passed=qa_passed,
        qa_error_text="；".join(qa_errors) if qa_errors else None,
    )


def _filter_objects_by_climbed_l0_version(
    objects: list[BomProcurementObject],
    nodes_by_id: dict[int, BomNode],
    bom_version: str | None,
) -> list[BomProcurementObject]:
    """列表浏览筛：先爬到所属 L0，再比树根 bom_version。禁止用 source 本行字。"""
    if not bom_version:
        return objects
    kept: list[BomProcurementObject] = []
    for item in objects:
        tree_root = l0_node_of(item.source_node_id, nodes_by_id)
        if tree_root is None or int(tree_root.level) != 0:
            continue
        if tree_root.bom_version == bom_version:
            kept.append(item)
    return kept


def _nodes_by_id(nodes: list[BomNode]) -> dict[int, BomNode]:
    return {node.id: node for node in nodes}


def _filter_price_rows(rows: list[PriceRow], keyword: str | None) -> list[PriceRow]:
    key = (keyword or "").casefold()
    if not key:
        return rows
    return [
        row
        for row in rows
        if key in (row.part_number or "").casefold() or key in (row.part_name or "").casefold()
    ]


def _month_columns(months: list[tuple[int, int]]) -> list[ProcurementContractMonthColumnVO]:
    return [
        ProcurementContractMonthColumnVO(year=year, month=month, header=month_header(year, month))
        for year, month in months
    ]


def _empty_hint(bundle: ReportBundle) -> str | None:
    if bundle.price_rows:
        return None
    if bundle.scope.view == VIEW_ASSEMBLY:
        return _EMPTY_ASSEMBLY_HINT
    if bundle.supplier_name:
        return f"供应商「{bundle.supplier_name}」在当前筛选下没有可展示的价目行。"
    return _EMPTY_OBJECT_HINT


def _to_row_vo(
    row: PriceRow,
    abbreviations: dict[str, str],
) -> ProcurementContractReportRowVO:
    names = [name for name in row.supplier_names if name]
    return ProcurementContractReportRowVO(
        seq_label=row.seq_label,
        internal_number=row.internal_number,
        part_number=row.part_number,
        part_name=row.part_name,
        supplier_name="、".join(names) or None,
        supplier_abbreviation="、".join(
            abbreviations.get(name) or _fallback_supplier_abbreviation(name) for name in names
        )
        or None,
        vehicle_qty=row.vehicle_qty,
        object_kind=row.object_kind,
        tooling_alloc_price=row.tooling_alloc_price,
        tooling_fee=row.tooling_fee,
        tooling_alloc_qty=row.tooling_alloc_qty,
        month_amounts=[
            ProcurementContractMonthAmountVO(
                year=cell.year,
                month=cell.month,
                should_cost=cell.should_cost,
            )
            for cell in row.month_amounts
        ],
    )


def _abbreviation_map(supplier_service: SupplierService, db: Session) -> dict[str, str]:
    return {vo.full_name: vo.abbreviation for vo in supplier_service.list_registered(db)}


_SUPPLIER_SUFFIXES = (
    "有限责任公司",
    "股份有限公司",
    "集团有限公司",
    "有限公司",
)


def _fallback_supplier_abbreviation(name: str) -> str:
    text = name.strip()
    for suffix in _SUPPLIER_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
            break
    if len(text) > 8:
        return text[:8]
    return text or name


def _to_filters(
    bundle: ReportBundle,
    query: ProcurementContractReportQuery,
) -> ProcurementContractReportFiltersVO:
    return ProcurementContractReportFiltersVO(
        location=query.location,
        vehicle_model=query.vehicle_model,
        bom_version=query.bom_version,
        start_year=query.start_year,
        start_month=query.start_month,
        end_year=query.end_year,
        end_month=query.end_month,
        supplier_name=bundle.supplier_name,
        keyword=query.keyword,
        view=bundle.scope.view,
        qa_passed=bundle.scope.qa_passed,
        qa_error_text=bundle.scope.qa_error_text,
        months=_month_columns(bundle.months),
        prep_row_count=len(bundle.prep_rows),
        price_row_count=len(bundle.price_rows),
        specified_supplier_count=len(bundle.supplier_names),
        window_month_count=len(bundle.months),
        missing_month_cell_count=bundle.missing_month_cell_count,
        empty_hint=_empty_hint(bundle),
        vehicle_total=bundle.vehicle_total,
        vehicle_total_skipped=bundle.vehicle_total_skipped,
    )
