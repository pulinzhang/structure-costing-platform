"""焊接价 + 摊入费用行。

包装运输表对不上时，运输/仓储捆包会记 note，金额仍用核价卡上的 0。
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bom.packaging_transport_fee import BomPackagingTransportFee
from app.models.costing.assembly_cost import AssemblyCost
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.schemas.vo.assembly_cost_restore_vo import (
    RestoreExceptionVO,
    RestoreIndirectLineVO,
    RestoreWeldingLineVO,
    RestoreWeldingVO,
)
from app.services.costing.assembly_cost.codes import (
    PURCHASED_ASSEMBLY_NOTE,
    card_short_code,
    is_purchased_assembly_root,
)
from app.services.costing.assembly_cost.restore.labels import (
    INDIRECT_KIND_LABELS,
    INDIRECT_UNIT_TRANSPORT,
    INDIRECT_WAREHOUSE_BUNDLING,
    WELDING_NONE_MESSAGE,
    indirect_kind,
)
from app.services.costing.assembly_cost.restore.money import _money, _opt_money


class RestoreWelding:
    def __init__(self, welding_repo: BomWeldingFeeRepository) -> None:
        self.welding_repo = welding_repo

    def _build_welding(
        self,
        db: Session,
        card: AssemblyCost,
        exceptions: list[RestoreExceptionVO],
    ) -> RestoreWeldingVO:
        if card.welding_fee_id is None:
            included = is_purchased_assembly_root(card.source_node_id, card.items)
            return RestoreWeldingVO(
                has_record=False,
                message=(PURCHASED_ASSEMBLY_NOTE if included else WELDING_NONE_MESSAGE),
                card_level=card.level,
            )
        fee = self.welding_repo.get_by_id(db, card.welding_fee_id)
        if fee is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的焊接价",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
            return RestoreWeldingVO(
                has_record=False,
                message="找不到当时的价",
                welding_fee_id=card.welding_fee_id,
                card_level=card.level,
            )
        mismatch = fee.level != card.level
        if mismatch:
            exceptions.append(
                RestoreExceptionVO(
                    kind="warning",
                    message=f"焊接层级对不上（表上是 {fee.level}，本件是 {card.level}），先用这条金额",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
        if fee.calc_status != "ok" or (fee.missing_price_count or 0) > 0:
            exceptions.append(
                RestoreExceptionVO(
                    kind="welding",
                    message=fee.calc_message or "焊接有缺价",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
        items = [
            RestoreWeldingLineVO(
                line_no=line.line_no,
                process_token=line.process_token,
                standard_process_name=line.standard_process_name,
                process_qty=Decimal(str(line.process_qty)),
                unit_price=_opt_money(line.unit_price),
                line_fee=_opt_money(line.line_fee),
                match_status=line.match_status,
                source_breakdown_line_id=line.source_breakdown_line_id,
            )
            for line in fee.items
        ]
        final_amount = fee.final_welding_fee
        if final_amount is None:
            final_amount = fee.total_welding_fee
        return RestoreWeldingVO(
            has_record=True,
            welding_fee_id=fee.id,
            weld_info_raw=fee.weld_info_raw,
            total_welding_fee=_opt_money(fee.total_welding_fee),
            other_fee=_opt_money(fee.other_fee),
            final_welding_fee=_opt_money(final_amount),
            calc_status=fee.calc_status,
            fee_level=fee.level,
            card_level=card.level,
            level_mismatch=mismatch,
            items=items,
        )

    def _build_indirects(
        self,
        card: AssemblyCost,
        packaging: BomPackagingTransportFee | None,
        exceptions: list[RestoreExceptionVO],
    ) -> list[RestoreIndirectLineVO]:
        lines: list[RestoreIndirectLineVO] = []
        match_key = f"{card.location} · {card.year} · {card.part_number}"
        for row in sorted(card.indirects, key=lambda item: (item.sort_no, item.id)):
            kind = indirect_kind(row.code)
            note = None
            if (
                row.code in {INDIRECT_UNIT_TRANSPORT, INDIRECT_WAREHOUSE_BUNDLING}
                and packaging is None
            ):
                note = "没有包装表这一行，所以是 0"
            lines.append(
                RestoreIndirectLineVO(
                    code=row.code,
                    label=INDIRECT_KIND_LABELS.get(row.code, row.label),
                    kind=kind,
                    amount=_money(row.amount),
                    rate=Decimal(str(row.rate)) if row.rate is not None else None,
                    base_amount=_opt_money(row.base_amount),
                    match_key=match_key if kind == "direct" else None,
                    note=note,
                )
            )
        return lines
