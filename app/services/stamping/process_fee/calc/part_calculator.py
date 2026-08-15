"""单零件加工费计算（工序循环 + 冲次单价匹配）。"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.stamping import StampingPart, StampingProcess
from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeFailedItemVO
from app.services.stamping.process_fee.calc.basis_text import build_process_basis_text
from app.services.stamping.process_fee.calc.constants import TONNAGE_SOURCE_SWING_SHEAR
from app.services.stamping.process_fee.calc.labels import (
    can_inherit_previous_tonnage,
    format_process_label,
    is_swing_shear_process,
    match_previous_process,
    summarize_processes,
)
from app.services.stamping.process_fee.calc.models import TonnageRateInfo
from app.services.stamping.process_fee.calc.tonnage_resolver import TonnageResolver
from app.services.stamping.process_fee.fee_math import FEE_QUANTIZE

logger = logging.getLogger("service.stamping.process_fee.calc")


class PartFeeCalculator:
    """按零件汇总各工序加工费。"""

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

    def _select_processes_for_calc(
        self,
        db: Session,
        part: StampingPart,
        processes: list[StampingProcess],
        prev_part_cache: dict[int, StampingPart | None],
    ) -> list[StampingProcess]:
        """
        共模/双槽/共用件以上一件工序方案为准。
        当前多出的工序视为录入错误，跳过不计费。
        """
        if not processes:
            return processes
        if not can_inherit_previous_tonnage(part, processes[0]):
            return processes

        previous_part = self.tonnage_resolver.get_previous_part(
            db, part, prev_part_cache
        )
        if previous_part is None:
            return processes

        previous_processes = list(previous_part.processes or [])
        if not previous_processes:
            return processes

        selected: list[StampingProcess] = []
        skipped_labels: list[str] = []
        for process in sorted(
            processes, key=lambda p: (p.process_order or 0, p.id or 0)
        ):
            if match_previous_process(process, previous_processes) is not None:
                selected.append(process)
            else:
                skipped_labels.append(format_process_label(process))

        if skipped_labels:
            logger.warning(
                "共模件跳过多余工序(以上一件为准): part=%s skipped=%s "
                "上一件 %s 工序清单：%s",
                part.part_number,
                "、".join(skipped_labels),
                previous_part.part_number,
                summarize_processes(previous_processes),
            )
        return selected

    def calc_part_fee(
        self,
        db: Session,
        part: StampingPart,
        rate_map: dict[int, TonnageRateInfo],
        year: int,
        prev_part_cache: dict[int, StampingPart | None],
    ) -> tuple[Decimal, int, list[dict]] | StampingProcessFeeFailedItemVO:
        processes = list(part.processes or [])
        if not processes:
            return self.build_failed_item(part, "无工序数据")

        processes = self._select_processes_for_calc(
            db, part, processes, prev_part_cache
        )
        if not processes:
            return self.build_failed_item(
                part, "共模件按上一件工序方案筛选后无有效工序"
            )

        total = Decimal("0")
        process_items: list[dict] = []
        for process in sorted(
            processes, key=lambda p: (p.process_order or 0, p.id or 0)
        ):
            process_label = format_process_label(process)
            original_tonnage = (
                int(process.tonnage) if process.tonnage is not None else None
            )

            if is_swing_shear_process(process):
                logger.info(
                    "摆剪工序加工费计 0: part=%s process=%s",
                    part.part_number,
                    process_label,
                )
                line_fee = Decimal("0").quantize(
                    FEE_QUANTIZE, rounding=ROUND_HALF_UP
                )
                process_items.append(
                    {
                        "source_process_id": process.id,
                        "process_seq": process.process_seq,
                        "process_order": process.process_order,
                        "process_code": process.process_code,
                        "original_tonnage": original_tonnage,
                        "resolved_tonnage": None,
                        "tonnage_source": TONNAGE_SOURCE_SWING_SHEAR,
                        "inherited_from_part_id": None,
                        "inherited_from_part_number": None,
                        "inherited_from_process_seq": None,
                        "inherited_from_process_code": None,
                        "cost_ratio": None,
                        "tonnage_price_id": None,
                        "price_per_stroke": None,
                        "line_fee": line_fee,
                        "basis_text": build_process_basis_text(
                            process_label=process_label,
                            tonnage_source=TONNAGE_SOURCE_SWING_SHEAR,
                            resolved_tonnage=None,
                            cost_ratio=None,
                            price_per_stroke=None,
                            line_fee=line_fee,
                        ),
                        "remark": process.remark,
                    }
                )
                continue

            tonnage_or_error = self.tonnage_resolver.resolve(
                db, part, process, prev_part_cache
            )
            if isinstance(tonnage_or_error, str):
                return self.build_failed_item(part, tonnage_or_error, process)

            resolved = tonnage_or_error

            if resolved.source == TONNAGE_SOURCE_SWING_SHEAR:
                line_fee = Decimal("0").quantize(
                    FEE_QUANTIZE, rounding=ROUND_HALF_UP
                )
                process_items.append(
                    {
                        "source_process_id": process.id,
                        "process_seq": process.process_seq,
                        "process_order": process.process_order,
                        "process_code": process.process_code,
                        "original_tonnage": original_tonnage,
                        "resolved_tonnage": None,
                        "tonnage_source": TONNAGE_SOURCE_SWING_SHEAR,
                        "inherited_from_part_id": resolved.inherited_from_part_id,
                        "inherited_from_part_number": (
                            resolved.inherited_from_part_number
                        ),
                        "inherited_from_process_seq": (
                            resolved.inherited_from_process_seq
                        ),
                        "inherited_from_process_code": (
                            resolved.inherited_from_process_code
                        ),
                        "cost_ratio": None,
                        "tonnage_price_id": None,
                        "price_per_stroke": None,
                        "line_fee": line_fee,
                        "basis_text": build_process_basis_text(
                            process_label=process_label,
                            tonnage_source=TONNAGE_SOURCE_SWING_SHEAR,
                            resolved_tonnage=None,
                            cost_ratio=None,
                            price_per_stroke=None,
                            line_fee=line_fee,
                            inherited_from_part_number=(
                                resolved.inherited_from_part_number
                            ),
                            inherited_from_process_seq=(
                                resolved.inherited_from_process_seq
                            ),
                            inherited_from_process_code=(
                                resolved.inherited_from_process_code
                            ),
                        ),
                        "remark": process.remark,
                    }
                )
                continue

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

            cost_ratio = Decimal(
                str(process.cost_ratio if process.cost_ratio is not None else 1)
            )
            price = rate_info.price_per_stroke
            line_raw = cost_ratio * price
            line_fee = line_raw.quantize(FEE_QUANTIZE, rounding=ROUND_HALF_UP)
            total += line_raw

            process_items.append(
                {
                    "source_process_id": process.id,
                    "process_seq": process.process_seq,
                    "process_order": process.process_order,
                    "process_code": process.process_code,
                    "original_tonnage": original_tonnage,
                    "resolved_tonnage": resolved.tonnage,
                    "tonnage_source": resolved.source,
                    "inherited_from_part_id": resolved.inherited_from_part_id,
                    "inherited_from_part_number": resolved.inherited_from_part_number,
                    "inherited_from_process_seq": resolved.inherited_from_process_seq,
                    "inherited_from_process_code": resolved.inherited_from_process_code,
                    "cost_ratio": cost_ratio,
                    "tonnage_price_id": rate_info.tonnage_price_id,
                    "price_per_stroke": price,
                    "line_fee": line_fee,
                    "basis_text": build_process_basis_text(
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
                    "remark": process.remark,
                }
            )

        return (
            total.quantize(FEE_QUANTIZE, rounding=ROUND_HALF_UP),
            len(process_items),
            process_items,
        )
