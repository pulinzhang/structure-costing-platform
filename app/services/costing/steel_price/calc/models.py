"""钢价计算编排 — 内部中间模型（非 API VO）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional


@dataclass
class SteelPriceCalcRequest:
    """计算入参（对齐 dashboard 钢价统计筛选）。"""

    year: int
    month: int
    location: str | None = None
    stamping_supplier: str | None = None
    vehicle_model: str | None = None


@dataclass
class MaterialThicknessRow:
    """Step1：冲压材料厚度规格（基地 + 钢种 + 厚度，三者缺一不可）。"""

    location: str
    material: str
    thickness: Decimal


@dataclass
class CalcRow:
    """计算中间行：随编排步骤逐步补齐字段。"""

    year: int
    month: int
    location: str
    grade: str
    thickness: Decimal

    # Step2 基价补齐
    steel_mill: str | None = None
    category_name: str | None = None
    width: Decimal | None = None
    base_thickness: Decimal | None = None
    base_price: Decimal | None = None
    processing_fee: Decimal = Decimal("0")
    base_price_id: int | None = None
    base_excel_filename: str | None = None
    base_sheet_name: str | None = None
    base_excel_row: int | None = None
    base_excel_col: int | None = None

    # Step3/4 加减价（厚度 / 宽度独立匹配）
    thickness_adjustment: Decimal = Decimal("0")
    width_adjustment: Decimal = Decimal("0")
    zinc_adjustment: Decimal = Decimal("0")
    other_adjustment: Decimal = Decimal("0")

    thickness_policy_id: int | None = None
    thickness_ladder_item_id: int | None = None
    thickness_excel_filename: str | None = None
    thickness_sheet_name: str | None = None
    thickness_excel_row: int | None = None
    thickness_excel_col: int | None = None

    width_policy_id: int | None = None
    width_ladder_item_id: int | None = None
    width_excel_filename: str | None = None
    width_sheet_name: str | None = None
    width_excel_row: int | None = None
    width_excel_col: int | None = None

    zinc_policy_id: int | None = None
    zinc_ladder_item_id: int | None = None
    zinc_excel_filename: str | None = None
    zinc_sheet_name: str | None = None
    zinc_excel_row: int | None = None
    zinc_excel_col: int | None = None

    # 元数据
    match_status: str = "no_base"
    calc_status: str = "failed"
    calc_message: Optional[str] = None
    messages: list[str] = field(default_factory=list)

    def add_message(self, message: str) -> None:
        self.messages.append(message)

    def finalize_status(self) -> None:
        """根据命中情况回写 match_status / calc_status / calc_message。"""
        has_base = self.base_price_id is not None and self.base_price is not None
        has_thickness = self.thickness_policy_id is not None
        has_width = self.width_policy_id is not None

        if not has_base:
            self.match_status = "no_base"
            self.calc_status = "failed"
        elif has_thickness and has_width:
            self.match_status = "full_match"
            self.calc_status = "success"
        elif has_thickness and not has_width:
            self.match_status = "no_width_policy"
            self.calc_status = "partial"
        elif has_width and not has_thickness:
            self.match_status = "no_thickness_policy"
            self.calc_status = "partial"
        else:
            self.match_status = "base_only"
            self.calc_status = "partial"

        self.calc_message = "；".join(self.messages) if self.messages else None

    def can_persist(self) -> bool:
        """是否具备落库必填字段（钢厂 / 大类 / 宽度 / 基价）。"""
        return (
            self.steel_mill is not None
            and self.category_name is not None
            and self.width is not None
            and self.base_price is not None
        )

    def to_persist_payload(self, *, calc_batch_id: str, formula_version: str) -> dict[str, Any]:
        """转为 SteelPriceService 落库 payload（仅可落库行）。"""
        steel_mill = self.steel_mill
        category_name = self.category_name
        width = self.width
        base_price = self.base_price
        if (
            steel_mill is None
            or category_name is None
            or width is None
            or base_price is None
        ):
            raise ValueError(
                "不可落库行缺少必填字段: "
                f"location={self.location} grade={self.grade} thickness={self.thickness}"
            )

        final_price = (
            Decimal(str(base_price))
            + Decimal(str(self.thickness_adjustment))
            + Decimal(str(self.width_adjustment))
            + Decimal(str(self.zinc_adjustment))
            + Decimal(str(self.processing_fee))
            + Decimal(str(self.other_adjustment))
        )
        thickness_f = float(self.thickness)
        width_f = float(width)
        return {
            "year": self.year,
            "month": self.month,
            "location": self.location,
            "steel_mill": steel_mill,
            "category_name": category_name,
            "grade": self.grade,
            "thickness": self.thickness,
            "width": width,
            "spec": f"{thickness_f:.2f}*{width_f:.2f}",
            "base_price": base_price,
            "thickness_adjustment": self.thickness_adjustment,
            "width_adjustment": self.width_adjustment,
            "zinc_adjustment": self.zinc_adjustment,
            "processing_fee": self.processing_fee,
            "other_adjustment": self.other_adjustment,
            "final_price_per_ton": final_price,
            "base_price_id": self.base_price_id,
            "base_excel_filename": self.base_excel_filename,
            "base_sheet_name": self.base_sheet_name,
            "base_excel_row": self.base_excel_row,
            "base_excel_col": self.base_excel_col,
            "thickness_policy_id": self.thickness_policy_id,
            "thickness_ladder_item_id": self.thickness_ladder_item_id,
            "thickness_excel_filename": self.thickness_excel_filename,
            "thickness_sheet_name": self.thickness_sheet_name,
            "thickness_excel_row": self.thickness_excel_row,
            "thickness_excel_col": self.thickness_excel_col,
            "width_policy_id": self.width_policy_id,
            "width_ladder_item_id": self.width_ladder_item_id,
            "width_excel_filename": self.width_excel_filename,
            "width_sheet_name": self.width_sheet_name,
            "width_excel_row": self.width_excel_row,
            "width_excel_col": self.width_excel_col,
            "zinc_policy_id": self.zinc_policy_id,
            "zinc_ladder_item_id": self.zinc_ladder_item_id,
            "zinc_excel_filename": self.zinc_excel_filename,
            "zinc_sheet_name": self.zinc_sheet_name,
            "zinc_excel_row": self.zinc_excel_row,
            "zinc_excel_col": self.zinc_excel_col,
            "calc_batch_id": calc_batch_id,
            "match_status": self.match_status,
            "calc_status": self.calc_status,
            "calc_message": self.calc_message,
            "formula_version": formula_version,
        }


@dataclass
class SteelPriceCalcResult:
    """编排结果摘要。"""

    calc_batch_id: str
    log_id: int | None = None
    status: str = "failed"
    material_count: int = 0
    enriched_count: int = 0
    no_base_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_approved_count: int = 0
    failed_count: int = 0
    detail_text: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    location: str | None = None
    stamping_supplier: str | None = None
    vehicle_model: str | None = None
    year: int | None = None
    month: int | None = None
