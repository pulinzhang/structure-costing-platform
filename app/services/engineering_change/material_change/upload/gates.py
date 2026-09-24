"""材料变更先验表、再对库。一条不过整本拒。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import listed, quoted
from app.common.period import format_period, period
from app.exceptions.base import BusinessException
from app.parsers.engineering_change.material_change.codes import (
    ECM_AFTER_EQUALS_BEFORE,
    ECM_AFTER_MATERIAL_UNKNOWN,
    ECM_BEFORE_MATERIAL,
    ECM_BEFORE_MATERIAL_UNKNOWN,
    ECM_BEFORE_THICKNESS,
    ECM_BYPRODUCT_FORBIDDEN,
    ECM_CUTOVER_NOT_LATER,
    ECM_DUPLICATE_CUTOVER,
    ECM_EFFECTIVE_MISMATCH,
    ECM_EFFECTIVE_TOO_EARLY,
    ECM_INTERCHANGE_REQUIRED,
    ECM_LOCATION_MISMATCH,
    ECM_MIXED_WITH_REVISE,
    ECM_OFFAL_FORBIDDEN,
    ECM_PART_NAME,
    ECM_PART_NOT_AS_OF,
    ECM_PENDING_VERSION,
    ECM_PROCESS_MATERIAL_CHANGED,
    ECM_PROJECT_MISMATCH,
    ECM_PROJECT_PERIOD,
    ECM_SUPPLIER_MISMATCH,
    ECM_SUPPLIER_UNKNOWN,
    ECM_TAILOR_WELD_FORBIDDEN,
    ECM_THICKNESS_DELTA,
    ECM_THICKNESS_FORMAT,
    ECM_VERSION_DUPLICATE,
    ECM_VERSION_FORMAT,
    ECM_VERSION_REQUIRED,
    INTERCHANGE_REQUIRED,
    ecm_row,
    ecm_sheet,
)
from app.parsers.engineering_change.material_change.order_parser import (
    MaterialChangeParsedRow,
    parse_material_change_workbook,
)
from app.repositories.engineering_change.material_change.upload_log_repository import (
    MaterialChangeUploadLogRepository,
)
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.stamping.part.engineering.service import (
    MISS_NOT_AS_OF,
    MISS_SUPPLIER_UNKNOWN,
    StampingEngineeringService,
)

_VERSION_RE = re.compile(r"^MAT-(\d{6})$")
_THICKNESS_RE = re.compile(r"^\d+(\.\d{1,2})?$")
_THICKNESS_MAX = Decimal("0.20")


def _tell(row: MaterialChangeParsedRow, column: str, code: str, how: str) -> str:
    return ecm_row(code, row.excel_row, column, how, row.part_number)


def _show_thickness(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


@dataclass(slots=True)
class MaterialChangeGatedRow:
    parsed: MaterialChangeParsedRow
    source_part_id: int
    before_thickness: Decimal
    after_thickness: Decimal


def gate_workbook(
    db: Session,
    *,
    file_content: bytes,
    page_location: str,
    page_vehicle_model: str,
    page_year: int,
    page_month: int,
    log_id: int,
) -> list[MaterialChangeGatedRow]:
    rows = parse_material_change_workbook(file_content)
    _gate_book_shape(rows, page_location, page_vehicle_model, page_year, page_month)
    _gate_pending(db, page_location, page_vehicle_model, page_year, page_month, log_id)
    try:
        VehicleModelService().require_introducible(
            db, page_location, page_vehicle_model, page_year, page_month
        )
    except BusinessException as error:
        raise BusinessException(f"{ECM_PROJECT_PERIOD}。{error}") from error
    sample = rows[0]
    duplicate = MaterialChangeUploadLogRepository().get_success_version(
        db,
        location=sample.location,
        vehicle_model=sample.vehicle_model,
        stamping_supplier=sample.stamping_supplier,
        change_version=sample.change_version,
    )
    if duplicate is not None:
        raise BusinessException(
            ecm_sheet(
                ECM_VERSION_DUPLICATE,
                f"版本{quoted(sample.change_version)}、厂{quoted(sample.stamping_supplier)}"
                "已经在列表里。请换更晚的月份，或先删掉原来那本。",
            )
        )
    return [_gate_row(db, row) for row in rows]


def _gate_book_shape(
    rows: list[MaterialChangeParsedRow],
    page_location: str,
    page_vehicle_model: str,
    page_year: int,
    page_month: int,
) -> None:
    locations = {row.location for row in rows}
    vehicles = {row.vehicle_model for row in rows}
    versions = {row.change_version for row in rows}
    periods = {(row.effective_year, row.effective_month) for row in rows}
    factories = {row.stamping_supplier for row in rows}
    if len(locations) != 1:
        raise BusinessException(
            ecm_sheet(
                ECM_LOCATION_MISMATCH,
                f"表里写成了{listed(locations)}。请整本改成同一个基地后再传。",
            )
        )
    if len(vehicles) != 1:
        raise BusinessException(
            ecm_sheet(
                ECM_PROJECT_MISMATCH,
                f"表里写成了{listed(vehicles)}。请整本改成同一个项目后再传。",
            )
        )
    if len(versions) != 1:
        raise BusinessException(
            ecm_sheet(
                ECM_VERSION_REQUIRED,
                f"表里写成了{listed(versions)}。请整本改成同一个变更版本后再传。",
            )
        )
    if len(periods) != 1:
        labels = [format_period(year, month) for year, month in sorted(periods)]
        raise BusinessException(
            ecm_sheet(
                ECM_EFFECTIVE_MISMATCH,
                f"表里写成了{listed(labels)}。请整本改成同一个月份后再传。",
            )
        )
    if len(factories) != 1:
        raise BusinessException(
            ecm_sheet(
                ECM_SUPPLIER_MISMATCH,
                f"表里写成了{listed(factories)}。请整本改成同一个冲压工厂后再传。",
            )
        )
    sample = rows[0]
    if sample.location != page_location:
        raise BusinessException(
            _tell(
                sample,
                "基地",
                ECM_LOCATION_MISMATCH,
                f"写成{quoted(sample.location)}，上传页是{quoted(page_location)}。请改成上传页上的字。",
            )
        )
    if sample.vehicle_model != page_vehicle_model:
        raise BusinessException(
            _tell(
                sample,
                "项目",
                ECM_PROJECT_MISMATCH,
                f"写成{quoted(sample.vehicle_model)}，上传页是{quoted(page_vehicle_model)}。"
                "请改成上传页上的字。",
            )
        )
    if sample.effective_year != page_year or sample.effective_month != page_month:
        raise BusinessException(
            _tell(
                sample,
                "生效年月",
                ECM_EFFECTIVE_MISMATCH,
                f"写成{quoted(format_period(sample.effective_year, sample.effective_month))}，"
                f"上传页是{quoted(format_period(page_year, page_month))}。请改成上传页那个月。",
            )
        )
    version_match = _VERSION_RE.match(sample.change_version)
    expected_digits = f"{page_year:04d}{page_month:02d}"
    expected = f"MAT-{expected_digits}"
    if version_match is None or version_match.group(1) != expected_digits:
        raise BusinessException(
            _tell(
                sample,
                "变更版本",
                ECM_VERSION_FORMAT,
                f"写成{quoted(sample.change_version)}。请改成{quoted(expected)}。",
            )
        )
    part_numbers: set[str] = set()
    for row in rows:
        if row.part_number in part_numbers:
            raise BusinessException(
                _tell(
                    row,
                    "零件号",
                    ECM_DUPLICATE_CUTOVER,
                    f"零件号{quoted(row.part_number)}写了不止一行。请删掉重复的行。",
                )
            )
        part_numbers.add(row.part_number)
        if row.change_version != sample.change_version:
            raise BusinessException(
                _tell(
                    row,
                    "变更版本",
                    ECM_VERSION_REQUIRED,
                    f"写成{quoted(row.change_version)}，第 {sample.excel_row} 行是"
                    f"{quoted(sample.change_version)}。请改成同一个版本。",
                )
            )
        if row.interchangeability != INTERCHANGE_REQUIRED:
            raise BusinessException(
                _tell(
                    row,
                    "互换性",
                    ECM_INTERCHANGE_REQUIRED,
                    f"写成{quoted(row.interchangeability)}。请改成{quoted(INTERCHANGE_REQUIRED)}。",
                )
            )
        if row.after_material == row.before_material:
            raise BusinessException(
                _tell(
                    row,
                    "变更后材料",
                    ECM_AFTER_EQUALS_BEFORE,
                    f"变更前和变更后都是{quoted(row.before_material)}。请把变更后改成要换成的牌号。",
                )
            )


def _gate_pending(
    db: Session,
    location: str,
    vehicle_model: str,
    year: int,
    month: int,
    log_id: int,
) -> None:
    pending = MaterialChangeUploadLogRepository().get_pending(
        db,
        location=location,
        vehicle_model=vehicle_model,
        effective_year=year,
        effective_month=month,
        exclude_id=log_id,
    )
    if pending is not None:
        raise BusinessException(
            ecm_sheet(
                ECM_PENDING_VERSION,
                f"{format_period(year, month)} 这一本还在导入。请等它结束再传。",
            )
        )


def _gate_row(
    db: Session,
    row: MaterialChangeParsedRow,
) -> MaterialChangeGatedRow:
    engineering = StampingEngineeringService()
    part, miss = engineering.get_part_as_of(
        db,
        location=row.location,
        stamping_supplier=row.stamping_supplier,
        vehicle_model=row.vehicle_model,
        part_number=row.part_number,
        as_of_year=row.effective_year,
        as_of_month=row.effective_month,
    )
    if miss == MISS_SUPPLIER_UNKNOWN:
        raise BusinessException(
            _tell(
                row,
                "冲压工厂",
                ECM_SUPPLIER_UNKNOWN,
                f"写成{quoted(row.stamping_supplier)}。请改成供应商档案里的全称。",
            )
        )
    if miss == MISS_NOT_AS_OF or part is None:
        raise BusinessException(
            _tell(
                row,
                "零件号",
                ECM_PART_NOT_AS_OF,
                f"零件号{quoted(row.part_number)}在"
                f"{format_period(row.effective_year, row.effective_month)}没有还能用的工艺。"
                "请核对零件号，或改到这个零件还在用的月份。",
            )
        )
    if part.location != row.location:
        raise BusinessException(
            _tell(
                row,
                "基地",
                ECM_LOCATION_MISMATCH,
                f"写成{quoted(row.location)}，工艺上是{quoted(part.location)}。请改成工艺上的字。",
            )
        )
    if part.vehicle_model != row.vehicle_model:
        raise BusinessException(
            _tell(
                row,
                "项目",
                ECM_PROJECT_MISMATCH,
                f"写成{quoted(row.vehicle_model)}，工艺上是{quoted(part.vehicle_model)}。"
                "请改成工艺上的字。",
            )
        )
    if part.stamping_supplier != row.stamping_supplier:
        raise BusinessException(
            _tell(
                row,
                "冲压工厂",
                ECM_SUPPLIER_MISMATCH,
                f"写成{quoted(row.stamping_supplier)}，工艺上是{quoted(part.stamping_supplier)}。"
                "请改成工艺上的全称。",
            )
        )
    if part.part_name != row.part_name:
        raise BusinessException(
            _tell(
                row,
                "零件名称",
                ECM_PART_NAME,
                f"写成{quoted(row.part_name)}，工艺上是{quoted(part.part_name)}。请改成工艺上那句。",
            )
        )
    if part.is_tailor_welded:
        raise BusinessException(
            _tell(row, "零件号", ECM_TAILOR_WELD_FORBIDDEN, "这是拼焊件。请把这一行从本子里删掉。")
        )
    if part.is_offal_nested:
        raise BusinessException(
            _tell(row, "零件号", ECM_OFFAL_FORBIDDEN, "这是利废件。请把这一行从本子里删掉。")
        )
    if part.is_scrap_byproduct:
        raise BusinessException(
            _tell(
                row,
                "零件号",
                ECM_BYPRODUCT_FORBIDDEN,
                "这是废料副产品。请把这一行从本子里删掉。",
            )
        )
    if period(row.effective_year, row.effective_month) < period(
        part.effective_year, part.effective_month
    ):
        raise BusinessException(
            _tell(
                row,
                "生效年月",
                ECM_EFFECTIVE_TOO_EARLY,
                f"这一行是{format_period(row.effective_year, row.effective_month)}，"
                f"工艺从{format_period(part.effective_year, part.effective_month)}才开始。"
                "请改到工艺开始之后的月份。",
            )
        )
    existing = engineering.list_material_changes(db, part.id)
    if existing:
        earliest = existing[0]
        if part.material != earliest.before_material:
            raise BusinessException(
                _tell(
                    row,
                    "变更前材料",
                    ECM_PROCESS_MATERIAL_CHANGED,
                    f"工艺上现在是{quoted(part.material)}，第一次材料变更前是"
                    f"{quoted(earliest.before_material)}。请先到列表删掉这个零件已有的材料变更，再重新传。",
                )
            )
        latest = existing[-1]
        if period(row.effective_year, row.effective_month) <= period(
            latest.effective_year, latest.effective_month
        ):
            raise BusinessException(
                _tell(
                    row,
                    "生效年月",
                    ECM_CUTOVER_NOT_LATER,
                    f"这一行是{format_period(row.effective_year, row.effective_month)}，"
                    f"已有变更到{format_period(latest.effective_year, latest.effective_month)}。"
                    "请改到那之后的月份。",
                )
            )
    _gate_mixed(
        row,
        part_effective_year=part.effective_year,
        part_effective_month=part.effective_month,
    )
    if not engineering.process_material_on_file(db, row.before_material):
        raise BusinessException(
            _tell(
                row,
                "变更前材料",
                ECM_BEFORE_MATERIAL_UNKNOWN,
                f"写成{quoted(row.before_material)}。请改成材料档案里已有的牌号。",
            )
        )
    if not engineering.process_material_on_file(db, row.after_material):
        raise BusinessException(
            _tell(
                row,
                "变更后材料",
                ECM_AFTER_MATERIAL_UNKNOWN,
                f"写成{quoted(row.after_material)}。请改成材料档案里已有的牌号。",
            )
        )
    expected = engineering.material_after_as_of(
        part.material,
        existing,
        as_of_year=row.effective_year,
        as_of_month=row.effective_month,
    )
    if row.before_material != expected:
        raise BusinessException(
            _tell(
                row,
                "变更前材料",
                ECM_BEFORE_MATERIAL,
                f"写成{quoted(row.before_material)}，这个月系统里用的是{quoted(expected)}。"
                f"请改成{quoted(expected)}。",
            )
        )
    before_t, after_t = _gate_thickness(row, part.thickness)
    return MaterialChangeGatedRow(
        parsed=row,
        source_part_id=part.id,
        before_thickness=before_t,
        after_thickness=after_t,
    )


def _gate_thickness(
    row: MaterialChangeParsedRow, process_thickness: Decimal | None
) -> tuple[Decimal, Decimal]:
    if _THICKNESS_RE.match(row.before_thickness) is None:
        raise BusinessException(
            _tell(
                row,
                "变更前料厚",
                ECM_THICKNESS_FORMAT,
                f"写成{quoted(row.before_thickness)}。请改成大于 0 的数字，最多两位小数，例如 1.5。",
            )
        )
    if _THICKNESS_RE.match(row.after_thickness) is None:
        raise BusinessException(
            _tell(
                row,
                "变更后料厚",
                ECM_THICKNESS_FORMAT,
                f"写成{quoted(row.after_thickness)}。请改成大于 0 的数字，最多两位小数，例如 1.5。",
            )
        )
    before_t = Decimal(row.before_thickness)
    after_t = Decimal(row.after_thickness)
    if before_t <= 0:
        raise BusinessException(
            _tell(
                row,
                "变更前料厚",
                ECM_THICKNESS_FORMAT,
                "料厚要大于 0。请改成大于 0 的数字，最多两位小数。",
            )
        )
    if after_t <= 0:
        raise BusinessException(
            _tell(
                row,
                "变更后料厚",
                ECM_THICKNESS_FORMAT,
                "料厚要大于 0。请改成大于 0 的数字，最多两位小数。",
            )
        )
    shown = _show_thickness(process_thickness) if process_thickness is not None else ""
    if process_thickness is None or before_t != process_thickness:
        expect = quoted(shown) if shown else "工艺上的料厚"
        raise BusinessException(
            _tell(
                row,
                "变更前料厚",
                ECM_BEFORE_THICKNESS,
                f"写成{quoted(row.before_thickness)}，工艺料厚是{expect}。请改成工艺上的数。",
            )
        )
    if abs(after_t - before_t) / before_t > _THICKNESS_MAX:
        raise BusinessException(
            _tell(
                row,
                "变更后料厚",
                ECM_THICKNESS_DELTA,
                f"变更前是{quoted(_show_thickness(before_t))}，变更后是{quoted(_show_thickness(after_t))}，"
                "相差超过两成。请把变更后料厚改近一些。",
            )
        )
    return before_t, after_t


def _gate_mixed(
    row: MaterialChangeParsedRow,
    *,
    part_effective_year: int,
    part_effective_month: int,
) -> None:
    if row.effective_year != part_effective_year or row.effective_month != part_effective_month:
        return
    raise BusinessException(
        _tell(
            row,
            "零件号",
            ECM_MIXED_WITH_REVISE,
            f"零件{quoted(row.part_number)}在"
            f"{format_period(row.effective_year, row.effective_month)}才开始有工艺。"
            "请换一个月再改材料。",
        )
    )
