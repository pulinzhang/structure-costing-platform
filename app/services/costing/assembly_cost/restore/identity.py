"""恒等式核对：卡上金额 vs 明细加总。

对不上写入 exceptions，前端按 identity 展示。
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.schemas.vo.assembly_cost_restore_vo import RestoreExceptionVO, RestoreIdentityCheckVO
from app.services.costing.assembly_cost.codes import card_short_code
from app.services.costing.assembly_cost.restore.labels import (
    HIGHLIGHT_ASSEMBLY_PRICE,
    HIGHLIGHT_TOTAL_COST,
)
from app.services.costing.assembly_cost.restore.money import _match, _money


class RestoreIdentity:
    def _identity_checks(
        self,
        card: AssemblyCost,
        items: list[AssemblyCostItem],
        exceptions: list[RestoreExceptionVO],
    ) -> list[RestoreIdentityCheckVO]:
        by_source: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for item in items:
            if item.cost_source == "skipped_by_bundle":
                continue
            by_source[item.cost_source] += _money(item.line_amount)
        stamp_sum = by_source["stamping"]
        purchased_sum = by_source["annual"]
        bundle_sum = by_source["bundle"]
        material_sum = _money(stamp_sum + purchased_sum + bundle_sum)
        total_sum = _money(
            material_sum + _money(card.welding_amount) + _money(card.welding_other_fee)
        )
        indirect_sum = _money(sum((_money(row.amount) for row in card.indirects), Decimal("0")))
        grand_sum = _money(total_sum + indirect_sum)
        checks = [
            RestoreIdentityCheckVO(
                code="stamping",
                label="冲压件",
                recorded=_money(card.stamping_amount),
                summed=stamp_sum,
                is_match=_match(card.stamping_amount, stamp_sum),
            ),
            RestoreIdentityCheckVO(
                code="purchased",
                label="分总成",
                recorded=_money(card.purchased_amount),
                summed=purchased_sum,
                is_match=_match(card.purchased_amount, purchased_sum),
            ),
            RestoreIdentityCheckVO(
                code="bundle",
                label="外购件",
                recorded=_money(card.bundle_amount),
                summed=bundle_sum,
                is_match=_match(card.bundle_amount, bundle_sum),
            ),
            RestoreIdentityCheckVO(
                code="material",
                label="零件合计",
                recorded=_money(card.material_amount),
                summed=material_sum,
                is_match=_match(card.material_amount, material_sum),
            ),
            RestoreIdentityCheckVO(
                code="total",
                label=HIGHLIGHT_TOTAL_COST,
                recorded=_money(card.total_amount),
                summed=total_sum,
                is_match=_match(card.total_amount, total_sum),
            ),
            RestoreIdentityCheckVO(
                code="should",
                label=f"{HIGHLIGHT_TOTAL_COST}（两处）",
                recorded=_money(card.should_cost),
                summed=_money(card.total_amount),
                is_match=_match(card.should_cost, card.total_amount),
            ),
            RestoreIdentityCheckVO(
                code="indirect",
                label="摊入费用",
                recorded=_money(card.indirect_amount),
                summed=indirect_sum,
                is_match=_match(card.indirect_amount, indirect_sum),
            ),
            RestoreIdentityCheckVO(
                code="grand",
                label=HIGHLIGHT_ASSEMBLY_PRICE,
                recorded=_money(card.grand_total),
                summed=_money(_money(card.total_amount) + _money(card.indirect_amount)),
                is_match=_match(
                    card.grand_total, _money(card.total_amount) + _money(card.indirect_amount)
                ),
            ),
        ]
        del grand_sum
        for check in checks:
            if not check.is_match:
                exceptions.append(
                    RestoreExceptionVO(
                        kind="identity",
                        message=f"{check.label}加总对不上",
                        short_code=card_short_code(
                            part_number=card.part_number, level=card.level, view="finance"
                        ),
                        part_number=card.part_number,
                    )
                )
        return checks
