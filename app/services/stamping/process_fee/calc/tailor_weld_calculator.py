"""拼焊件加工费计算。

与普通件 / 左右共模分开：不按上一件工序清单裁剪（保留「两块方料&拼焊」）。

工序规则：
  1. 「两块方料&拼焊」或摆剪 → 计 0，不查冲次单价
  2. 自有吨位 > 0 → 按本工序吨位直接算
  3. 缺吨位且双槽/合并/共用 → 继承上一件（序号减 1）对应工序
  4. 其它 → 失败

不按子片数翻倍：拼焊板先焊再冲，压机工序只计一套。
拼焊费由列表「其它费用」录入，不在本计算器内。
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal

from app.models.stamping import StampingPart, StampingProcess
from app.schemas.dto.stamping_process_fee_dto import ProcessFeeItemPayload
from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeFailedItemVO
from app.services.stamping.process_fee.calc.basis_text import build_process_basis_text
from app.services.stamping.process_fee.calc.constants import (
    TONNAGE_SOURCE_SWING_SHEAR,
    TONNAGE_SOURCE_TAILOR_WELD,
)
from app.services.stamping.process_fee.calc.labels import (
    format_process_label,
    is_swing_shear_process,
    is_tailor_weld_describe_process,
    self_tonnage,
)
from app.services.stamping.process_fee.calc.models import (
    ProcessTonnageResolveResult,
    TonnageRateInfo,
)
from app.services.stamping.process_fee.calc.previous_part import PreviousPartIndex
from app.services.stamping.process_fee.calc.tonnage_resolver import TonnageResolver
from app.services.stamping.process_fee.fee_math import FEE_QUANTIZE

logger = logging.getLogger("service.stamping.process_fee.calc")


class TailorWeldFeeCalculator:
    """拼焊总成加工费：父件工序列表走一遍，子片不参与本层。"""

    def __init__(self, tonnage_resolver: TonnageResolver | None = None) -> None:
        self.tonnage_resolver = tonnage_resolver or TonnageResolver()

    @staticmethod
    def build_failed_item(
        part: StampingPart,
        reason: str,
        process: StampingProcess | None = None,
    ) -> StampingProcessFeeFailedItemVO:
        return StampingProcessFeeFailedItemVO(
            part_number=part.part_number,
            part_name=part.part_name,
            process_seq=(process.process_seq if process else None),
            process_code=(process.process_code if process else None),
            process_method=part.process_method,
            reason=reason,
        )

    def calc_part_fee(
        self,
        part: StampingPart,
        rate_map: dict[int, TonnageRateInfo],
        year: int,
        previous_parts: PreviousPartIndex | None = None,
    ) -> tuple[Decimal, int, list[ProcessFeeItemPayload]] | StampingProcessFeeFailedItemVO:
        processes = list(part.processes or [])
        if not processes:
            return self.build_failed_item(part, "拼焊件无工序数据")

        previous_parts = previous_parts or PreviousPartIndex()

        total = Decimal("0")
        process_items: list[ProcessFeeItemPayload] = []
        for process in sorted(processes, key=lambda p: (p.process_order or 0, p.id or 0)):
            process_label = format_process_label(process)
            original_tonnage = self_tonnage(process)

            if is_tailor_weld_describe_process(process):
                logger.info(
                    "拼焊描述工序加工费计 0: part=%s process=%s",
                    part.part_number,
                    process_label,
                )
                process_items.append(
                    self._zero_fee_item(
                        process,
                        process_label,
                        original_tonnage,
                        TONNAGE_SOURCE_TAILOR_WELD,
                    )
                )
                continue

            if is_swing_shear_process(process):
                logger.info(
                    "拼焊件摆剪工序加工费计 0: part=%s process=%s",
                    part.part_number,
                    process_label,
                )
                process_items.append(
                    self._zero_fee_item(
                        process,
                        process_label,
                        original_tonnage,
                        TONNAGE_SOURCE_SWING_SHEAR,
                    )
                )
                continue

            tonnage_or_error = self.tonnage_resolver.resolve(part, process, previous_parts)
            if isinstance(tonnage_or_error, str):
                return self.build_failed_item(part, tonnage_or_error, process)

            resolved = tonnage_or_error
            if resolved.source == TONNAGE_SOURCE_SWING_SHEAR:
                process_items.append(
                    self._zero_fee_item(
                        process,
                        process_label,
                        original_tonnage,
                        TONNAGE_SOURCE_SWING_SHEAR,
                        resolved=resolved,
                    )
                )
                continue

            press_or_error = self._press_fee_item(
                part, process, process_label, original_tonnage, resolved, rate_map, year
            )
            if isinstance(press_or_error, StampingProcessFeeFailedItemVO):
                return press_or_error

            line_item, line_raw = press_or_error
            total += line_raw
            process_items.append(line_item)

        return (
            total.quantize(FEE_QUANTIZE, rounding=ROUND_HALF_UP),
            len(process_items),
            process_items,
        )

    def _zero_fee_item(
        self,
        process: StampingProcess,
        process_label: str,
        original_tonnage: int | None,
        tonnage_source: str,
        resolved: ProcessTonnageResolveResult | None = None,
    ) -> ProcessFeeItemPayload:
        line_fee = Decimal("0").quantize(FEE_QUANTIZE, rounding=ROUND_HALF_UP)
        inherited_part_number = resolved.inherited_from_part_number if resolved else None
        inherited_process_seq = resolved.inherited_from_process_seq if resolved else None
        inherited_process_code = resolved.inherited_from_process_code if resolved else None
        return ProcessFeeItemPayload(
            source_process_id=process.id,
            process_seq=process.process_seq,
            process_order=process.process_order,
            process_code=process.process_code,
            original_tonnage=original_tonnage,
            resolved_tonnage=None,
            tonnage_source=tonnage_source,
            inherited_from_part_id=(resolved.inherited_from_part_id if resolved else None),
            inherited_from_part_number=inherited_part_number,
            inherited_from_process_seq=inherited_process_seq,
            inherited_from_process_code=inherited_process_code,
            cost_ratio=None,
            tonnage_price_id=None,
            price_per_stroke=None,
            line_fee=line_fee,
            basis_text=build_process_basis_text(
                process_label=process_label,
                tonnage_source=tonnage_source,
                resolved_tonnage=None,
                cost_ratio=None,
                price_per_stroke=None,
                line_fee=line_fee,
                inherited_from_part_number=inherited_part_number,
                inherited_from_process_seq=inherited_process_seq,
                inherited_from_process_code=inherited_process_code,
            ),
            remark=process.remark,
        )

    def _press_fee_item(
        self,
        part: StampingPart,
        process: StampingProcess,
        process_label: str,
        original_tonnage: int | None,
        resolved: ProcessTonnageResolveResult,
        rate_map: dict[int, TonnageRateInfo],
        year: int,
    ) -> tuple[ProcessFeeItemPayload, Decimal] | StampingProcessFeeFailedItemVO:
        if resolved.tonnage is None:
            return self.build_failed_item(
                part,
                f"当前工序 {process_label} 缺少吨位",
                process,
            )

        rate_info = rate_map.get(resolved.tonnage)
        if rate_info is None:
            location = (part.location or "").strip() or "(空)"
            return self.build_failed_item(
                part,
                f"当前工序 {process_label} 吨位 {resolved.tonnage}T "
                f"在基地「{location}」{year} 年无冲次单价"
                f"（须年度、基地、吨位均匹配）",
                process,
            )

        cost_ratio = Decimal(str(process.cost_ratio if process.cost_ratio is not None else 1))
        price = rate_info.price_per_stroke
        line_raw = cost_ratio * price
        line_fee = line_raw.quantize(FEE_QUANTIZE, rounding=ROUND_HALF_UP)
        item = ProcessFeeItemPayload(
            source_process_id=process.id,
            process_seq=process.process_seq,
            process_order=process.process_order,
            process_code=process.process_code,
            original_tonnage=original_tonnage,
            resolved_tonnage=resolved.tonnage,
            tonnage_source=resolved.source,
            inherited_from_part_id=resolved.inherited_from_part_id,
            inherited_from_part_number=resolved.inherited_from_part_number,
            inherited_from_process_seq=resolved.inherited_from_process_seq,
            inherited_from_process_code=resolved.inherited_from_process_code,
            cost_ratio=cost_ratio,
            tonnage_price_id=rate_info.tonnage_price_id,
            price_per_stroke=price,
            line_fee=line_fee,
            basis_text=build_process_basis_text(
                process_label=process_label,
                tonnage_source=resolved.source,
                resolved_tonnage=resolved.tonnage,
                cost_ratio=cost_ratio,
                price_per_stroke=price,
                line_fee=line_fee,
                inherited_from_part_number=resolved.inherited_from_part_number,
                inherited_from_process_seq=resolved.inherited_from_process_seq,
                inherited_from_process_code=resolved.inherited_from_process_code,
            ),
            remark=process.remark,
        )
        return item, line_raw
