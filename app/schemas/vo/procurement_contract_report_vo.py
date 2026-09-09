"""采购价格查询 / 预检 VO。"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.common.money import Q4, optional_format_money


class ProcurementContractMonthAmountVO(BaseModel):
    year: int
    month: int
    should_cost: Decimal | None = None

    @field_serializer("should_cost")
    def serialize_should_cost(self, value: Decimal | None) -> str:
        if value is None:
            return "/"
        return optional_format_money(value, Q4, 4) or "/"


class ProcurementContractMonthColumnVO(BaseModel):
    year: int
    month: int
    header: str


class ProcurementContractReportRowVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq_label: str
    internal_number: str | None = None
    part_number: str
    part_name: str | None = None
    supplier_name: str | None = None
    supplier_abbreviation: str | None = None
    vehicle_qty: Decimal
    qty_unit: str = "件"
    object_kind: str | None = None
    pay_tooling_separately: str = "N"
    tooling_alloc_price: Decimal | None = None
    tooling_fee: Decimal | None = None
    tooling_alloc_qty: Decimal | None = None
    month_amounts: list[ProcurementContractMonthAmountVO]

    @field_serializer("vehicle_qty")
    def serialize_qty(self, value: Decimal) -> str:
        return f"{value.normalize()}"

    @field_serializer("tooling_alloc_price", "tooling_fee")
    def serialize_tooling_money(self, value: Decimal | None) -> str:
        if value is None:
            return "/"
        return optional_format_money(value, Q4, 4) or "/"

    @field_serializer("tooling_alloc_qty")
    def serialize_alloc_qty(self, value: Decimal | None) -> str:
        if value is None:
            return "/"
        return f"{value.quantize(Decimal('1'))}"


class ProcurementContractReportFiltersVO(BaseModel):
    location: str
    vehicle_model: str
    bom_version: str
    start_year: int
    start_month: int
    end_year: int
    end_month: int
    supplier_name: str | None = None
    keyword: str | None = None
    view: str = "procurement"
    qa_passed: bool
    qa_error_text: str | None = None
    months: list[ProcurementContractMonthColumnVO]
    prep_row_count: int
    price_row_count: int
    specified_supplier_count: int
    window_month_count: int
    missing_month_cell_count: int
    empty_hint: str | None = None
    vehicle_total: Decimal | None = None
    vehicle_total_skipped: int = 0

    @field_serializer("vehicle_total")
    def serialize_vehicle_total(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return optional_format_money(value, Q4, 4)


class ProcurementContractOpenDefaultsVO(BaseModel):
    location: str | None = None
    vehicle_model: str | None = None
    bom_version: str | None = None
    start_year: int | None = None
    start_month: int | None = None
    end_year: int | None = None
    end_month: int | None = None


class ProcurementContractReportPrepVO(BaseModel):
    view: str = "procurement"
    qa_passed: bool
    qa_error_text: str | None = None
    months: list[ProcurementContractMonthColumnVO]
    supplier_names: list[str] = Field(default_factory=list)
    prep_row_count: int
    price_row_count: int
    specified_supplier_count: int
    window_month_count: int
    missing_month_cell_count: int
    empty_hint: str | None = None
    vehicle_total: Decimal | None = None
    vehicle_total_skipped: int = 0

    @field_serializer("vehicle_total")
    def serialize_vehicle_total(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return optional_format_money(value, Q4, 4)
