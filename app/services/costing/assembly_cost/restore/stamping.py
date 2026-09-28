"""冲压件卡片：工序/模具/钢价/废料，以及断链异常。

树结构在 tree.py。
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.models.costing.stamping_part_cost import StampingPartCost
from app.models.costing.steel_price import SteelPrice
from app.models.stamping.die_fee import StampingDieFee
from app.models.stamping.gauge_fee import StampingGaugeFee
from app.models.stamping.process_fee import StampingProcessFee
from app.models.yishiyiyi.scrap_price import StampingScrapPrice
from app.models.yishiyiyi.steel_base_price import SteelBasePrice
from app.schemas.vo.assembly_cost_restore_vo import (
    RestoreDieOpVO,
    RestoreDocumentRefVO,
    RestoreExceptionVO,
    RestoreProcessOpVO,
    RestoreStampingVO,
    RestoreSteelVO,
)
from app.services.costing.assembly_cost.restore.documents import RestoreDocuments
from app.services.costing.assembly_cost.restore.money import _money, _opt_money


class RestoreStamping:
    def __init__(self, documents: RestoreDocuments) -> None:
        self._documents = documents

    def _build_stamping(
        self,
        *,
        db: Session,
        item: AssemblyCostItem,
        short: str,
        rows: list[StampingPartCost],
        process_map: dict[int, StampingProcessFee],
        die_map: dict[int, StampingDieFee],
        gauge_map: dict[int, StampingGaugeFee],
        steel_map: dict[int, SteelPrice],
        base_price_map: dict[int, SteelBasePrice],
        scrap_map: dict[int, StampingScrapPrice],
        exceptions: list[RestoreExceptionVO],
        documents: list[RestoreDocumentRefVO],
    ) -> RestoreStampingVO:
        if not rows:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
            return RestoreStampingVO(record_missing=True, missing_reason="找不到当时的价")
        costs = {_money(row.unit_cost) for row in rows}
        note = None
        if len(rows) > 1 and len(costs) == 1:
            note = "几家工厂价一样"
        picked = rows[0]
        process_row = process_map.get(picked.process_fee_id) if picked.process_fee_id else None
        die_row = die_map.get(picked.die_fee_id) if picked.die_fee_id else None
        if picked.process_fee_id and process_row is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的工序价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
        if picked.die_fee_id and die_row is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的模具价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
        steel = self._build_steel(
            picked, steel_map, base_price_map, exceptions, short, item.part_number
        )
        scrap_exists = bool(picked.scrap_price_id and picked.scrap_price_id in scrap_map)
        if picked.scrap_price_id and not scrap_exists:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的废料价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
        process_ops = self._process_ops(process_row)
        die_ops = self._die_ops(die_row)
        part_filename = (picked.excel_filename or "").strip()
        if part_filename:
            self._documents._add_document(
                documents,
                file_category="stamping_part",
                filename=part_filename,
                excel_row=picked.excel_row,
                short_code=short,
            )
        process_filename = (
            (process_row.excel_filename or "").strip() if process_row is not None else ""
        )
        if process_filename and process_filename != part_filename:
            self._documents._add_document(
                documents,
                file_category="stamping_process_fee",
                filename=process_filename,
                excel_row=None,
                short_code=short,
            )
        if process_row is not None:
            self._documents._add_tonnage_documents(
                db,
                documents,
                location=process_row.location,
                year=process_row.year,
                short_code=short,
            )
        if die_row is not None and die_row.excel_filename:
            self._documents._add_document(
                documents,
                file_category="stamping_die",
                filename=die_row.excel_filename,
                excel_row=None,
                short_code=short,
            )
        if steel is not None and steel.base_excel_filename:
            self._documents._add_document(
                documents,
                file_category="steel_base_price",
                filename=steel.base_excel_filename,
                excel_row=steel.base_excel_row,
                short_code=short,
            )
        if steel is not None and steel.thickness_excel_filename:
            self._documents._add_document(
                documents,
                file_category="steel_thickness_policy",
                filename=steel.thickness_excel_filename,
                excel_row=steel.thickness_excel_row,
                short_code=short,
            )
        gauge_exists = bool(picked.gauge_fee_id and picked.gauge_fee_id in gauge_map)
        if picked.gauge_fee_id and not gauge_exists:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的检具价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
        return RestoreStampingVO(
            record_id=picked.id,
            record_missing=False,
            stamping_supplier=picked.stamping_supplier,
            same_unit_cost_note=note,
            unit_cost=_opt_money(picked.unit_cost),
            direct_cost=_opt_money(picked.direct_cost),
            formula_version=picked.formula_version,
            is_offal_nested=bool(picked.is_offal_nested),
            offal_source=picked.offal_source,
            material_amount_sheet=_opt_money(picked.material_amount_sheet),
            loss_scrap_deduction=_opt_money(picked.loss_scrap_deduction),
            process_scrap_deduction=_opt_money(picked.process_scrap_deduction),
            material_net_per_part=_opt_money(picked.material_net_per_part),
            blank_weight_kg=Decimal(str(picked.blank_weight_kg))
            if picked.blank_weight_kg is not None
            else None,
            finished_total_kg=_opt_money(picked.finished_total_kg),
            scrap_weight_kg=_opt_money(picked.scrap_weight_kg),
            density=_opt_money(picked.density),
            material_loss_rate=Decimal(str(picked.material_loss_rate))
            if picked.material_loss_rate is not None
            else None,
            scrap_recovery_rate=Decimal(str(picked.scrap_recovery_rate))
            if picked.scrap_recovery_rate is not None
            else None,
            material=(picked.material or "").strip() or None,
            sheet_length=_opt_money(picked.sheet_length),
            sheet_width=_opt_money(picked.sheet_width),
            thickness=_opt_money(picked.thickness),
            parts_per_sheet=picked.parts_per_sheet,
            swing_shear_fee_per_ton=_opt_money(picked.swing_shear_fee_per_ton),
            steel=steel,
            scrap_price_id=picked.scrap_price_id,
            scrap_ton_price=_opt_money(picked.scrap_ton_price),
            scrap_record_exists=scrap_exists or picked.scrap_price_id is None,
            process_fee_id=picked.process_fee_id,
            process_fee_amount=_opt_money(picked.process_fee_amount),
            process_excel_filename=process_row.excel_filename if process_row is not None else None,
            process_ops=process_ops,
            die_fee_id=picked.die_fee_id,
            die_fee_amount=_opt_money(picked.die_fee_amount),
            die_system_fee=_opt_money(die_row.die_fee) if die_row is not None else None,
            die_adjustment_amount=_opt_money(die_row.adjustment_amount)
            if die_row is not None
            else None,
            die_unit_price=_opt_money(die_row.unit_price) if die_row is not None else None,
            die_allocation_qty=_opt_money(die_row.allocation_qty) if die_row is not None else None,
            die_price_kind=die_row.price_kind if die_row is not None else None,
            die_excel_filename=die_row.excel_filename if die_row is not None else None,
            die_ops=die_ops,
            gauge_fee_id=picked.gauge_fee_id,
            gauge_fee_amount=_opt_money(picked.gauge_fee_amount),
            gauge_record_exists=gauge_exists or picked.gauge_fee_id is None,
            finished_finance_fee=_opt_money(picked.finished_finance_fee),
            finished_management_fee=_opt_money(picked.finished_management_fee),
            finished_warehouse_packaging_fee=_opt_money(picked.finished_warehouse_packaging_fee),
            finished_pretax_profit_fee=_opt_money(picked.finished_pretax_profit_fee),
            excel_filename=picked.excel_filename,
            excel_row=picked.excel_row,
        )

    def _build_steel(
        self,
        picked: StampingPartCost,
        steel_map: dict[int, SteelPrice],
        base_price_map: dict[int, SteelBasePrice],
        exceptions: list[RestoreExceptionVO],
        short: str,
        part_number: str,
    ) -> RestoreSteelVO:
        if picked.steel_price_id is None:
            return RestoreSteelVO(
                steel_mill=picked.steel_mill,
                steel_ton_price=_opt_money(picked.steel_ton_price),
                record_exists=False,
            )
        row = steel_map.get(picked.steel_price_id)
        if row is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的钢价",
                    short_code=short,
                    part_number=part_number,
                )
            )
            return RestoreSteelVO(
                steel_mill=picked.steel_mill,
                steel_ton_price=_opt_money(picked.steel_ton_price),
                steel_price_id=picked.steel_price_id,
                record_exists=False,
                missing_reason="找不到当时的钢价",
            )
        base_row = base_price_map.get(row.base_price_id) if row.base_price_id else None
        filename = None
        excel_row = None
        if base_row is not None:
            filename = base_row.excel_filename
            excel_row = base_row.excel_row
        elif row.base_excel_filename:
            filename = row.base_excel_filename
            excel_row = row.base_excel_row
        return RestoreSteelVO(
            steel_mill=picked.steel_mill or row.steel_mill,
            steel_ton_price=_opt_money(picked.steel_ton_price),
            steel_price_id=picked.steel_price_id,
            record_exists=True,
            base_price=_opt_money(row.base_price),
            thickness_adjustment=_opt_money(row.thickness_adjustment),
            width_adjustment=_opt_money(row.width_adjustment),
            zinc_adjustment=_opt_money(row.zinc_adjustment),
            processing_fee=_opt_money(row.processing_fee),
            other_adjustment=_opt_money(row.other_adjustment),
            final_price_per_ton=_opt_money(row.final_price_per_ton),
            base_excel_filename=filename,
            base_excel_row=excel_row,
            thickness_excel_filename=row.thickness_excel_filename,
            thickness_excel_row=row.thickness_excel_row,
        )

    def _process_ops(self, process_row: StampingProcessFee | None) -> list[RestoreProcessOpVO]:
        if process_row is None:
            return []
        ops: list[RestoreProcessOpVO] = []
        for op in process_row.process_items:
            ops.append(
                RestoreProcessOpVO(
                    process_seq=op.process_seq,
                    process_code=op.process_code,
                    original_tonnage=op.original_tonnage,
                    resolved_tonnage=op.resolved_tonnage,
                    tonnage_source=op.tonnage_source,
                    inherited_from_part_number=op.inherited_from_part_number,
                    inherited_from_process_seq=op.inherited_from_process_seq,
                    cost_ratio=_opt_money(op.cost_ratio),
                    price_per_stroke=_opt_money(op.price_per_stroke),
                    line_fee=_money(op.line_fee),
                    basis_text=op.basis_text,
                )
            )
        return ops

    def _die_ops(self, die_row: StampingDieFee | None) -> list[RestoreDieOpVO]:
        if die_row is None:
            return []
        return [
            RestoreDieOpVO(
                process_seq=op.process_seq,
                process_code=op.process_code,
                estimated_weight_t=_opt_money(op.estimated_weight_t),
                alloc_ratio=_opt_money(op.alloc_ratio),
                die_sets=op.die_sets,
                unit_price=_money(op.unit_price),
                allocation_qty=_opt_money(op.allocation_qty),
                price_kind=op.price_kind,
                line_die_fee=_money(op.line_die_fee),
                basis_text=op.basis_text,
            )
            for op in die_row.items
        ]
