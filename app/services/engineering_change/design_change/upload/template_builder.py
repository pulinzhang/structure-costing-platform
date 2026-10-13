"""设计变更导入模板。五种改法各一个总成。增加分总成是一套一级节点，下面至少两颗二级。"""

from __future__ import annotations

import re
from copy import copy
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol, cast

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.cell_style import StyleArray
from openpyxl.worksheet.worksheet import Worksheet

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_ADD_SUBASSEMBLY,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    PART_LEVEL_ASSEMBLY,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
)
from app.parsers.engineering_change.design_change.change_order_parser import CHANGE_ORDER_HEADERS
from app.parsers.engineering_change.design_change.sheet_extract import (
    SHEET_CHANGE_ORDER,
    SHEET_CHANGE_ORDER_HINT,
)
from app.services.bom.bom.upload.template_builder import build_bom_material_template
from app.services.stamping.part.upload.template_builder import build_stamping_process_template

TEMPLATE_FILENAME = "设计变更导入模板.xlsx"

LOCATION = "青岛"
VEHICLE_MODEL = "T28"
CUSTOMER_NAME = "奇瑞公司"
PERIOD_LABEL = "2026年07月"
_PERIOD_LABEL_RE = re.compile(r"^(\d{4})年(\d{1,2})月$")
# Excel 中文区域内置格式 yyyy"年"m"月"。打开显示「2026年7月」，文件里存的是日期序列号。
_EXCEL_YEAR_MONTH_FORMAT_ID = 57
_EXCEL_EPOCH = datetime(1899, 12, 30)
CHANGE_VERSION = "EC-202607"
STAMPING_SUPPLIER = "烟台海众汽车零部件有限公司"
BOM_VERSION_LABEL = "D/00"
HEADER_DATE = "2026-07-01"
DOC_NO = "EC-T28-202607"
SLASH = "/"
ADD_PART_NUMBER = "EX-ADD-1AB"
LEAF_BEFORE = "EX-LEAF-AA"
LEAF_AFTER = "EX-LEAF-AB"
LEAF_SUB = "EX-LEAF-SUB-AA-1"
LEAF_ADD = "EX-LEAF-ADD-1AA"
LEAF_NUT = "EX-LEAF-NUT-1"
_ASSEMBLY_CHANGE_ORDER_COLS = (3, 4, 5)


@dataclass(frozen=True, slots=True)
class TemplateMeta:
    """表头。不传项目时用青岛 T28，只给测试；下载会换成所选基地和项目。零件号不在这里。"""

    location: str = LOCATION
    vehicle_model: str = VEHICLE_MODEL
    customer_name: str = CUSTOMER_NAME
    period_label: str = PERIOD_LABEL
    change_version: str = CHANGE_VERSION
    stamping_supplier: str = STAMPING_SUPPLIER
    bom_version_label: str = BOM_VERSION_LABEL
    header_date: str = HEADER_DATE
    doc_no: str = DOC_NO


DEFAULT_META = TemplateMeta()

_THIN = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_DATA_FONT = Font(name="微软雅黑", size=9)
_NOT_ASSEMBLED_FILL = PatternFill("solid", fgColor="FFE4E4")
_ADD_PART_FILL = PatternFill("solid", fgColor="E2EFDA")


@dataclass(frozen=True, slots=True)
class ChangeOrderSample:
    change_type: str
    before_assembly: str
    after_assembly: str | None
    assembly_name: str
    part_level: str
    before_part: str | None
    after_part: str | None
    part_name: str | None


@dataclass(frozen=True, slots=True)
class BomSample:
    seq_no: int
    internal_number: str
    part_number: str
    part_name: str
    weld_info: str
    l1_internal: str
    l1_part_number: str
    l1_part_name: str
    l1_qty: int | str
    l1_weld: str
    l2_internal: str
    l2_part_number: str
    l2_part_name: str
    l2_qty: int | str
    material: str
    thickness_text: str
    part_weight: float
    gauge_developed: str
    remark: str | None
    is_not_assembled: bool = False
    is_added_part: bool = False
    blank_assembly: bool = False
    blank_l1: bool = False
    part_sketch: bool = False
    group_part_number: str = ""


@dataclass(frozen=True, slots=True)
class ProcessSample:
    part_number: str
    part_name: str
    material: str
    thickness: float
    part_weight: float
    sheet_length: int
    sheet_width: int
    parts_per_sheet: int
    sheet_type: str
    process_seq: str
    process_code: str
    die_sets: int
    tonnage: int | None
    die_type: str


@dataclass(frozen=True, slots=True)
class TemplateBook:
    change_orders: tuple[ChangeOrderSample, ...]
    bom: tuple[BomSample, ...]
    process: tuple[ProcessSample, ...]
    change_order_note: str
    meta: TemplateMeta = DEFAULT_META


def _grouped_process_parts(
    process_samples: tuple[ProcessSample, ...],
) -> list[tuple[int, tuple[ProcessSample, ...]]]:
    groups: dict[str, list[ProcessSample]] = {}
    order: list[str] = []
    for sample in process_samples:
        if sample.part_number not in groups:
            groups[sample.part_number] = []
            order.append(sample.part_number)
        groups[sample.part_number].append(sample)
    return [
        (seq_no, tuple(groups[part_number])) for seq_no, part_number in enumerate(order, start=1)
    ]


def _assembly_change_order_key(sample: ChangeOrderSample) -> tuple[str, str, str]:
    return (sample.before_assembly, sample.after_assembly or "", sample.assembly_name)


def _merge_same_assembly_change_order_rows(
    sheet: Worksheet,
    change_orders: tuple[ChangeOrderSample, ...],
    first_row: int,
) -> None:
    start = 0
    while start < len(change_orders):
        end = start
        key = _assembly_change_order_key(change_orders[start])
        while (
            end + 1 < len(change_orders)
            and _assembly_change_order_key(change_orders[end + 1]) == key
        ):
            end += 1
        if end > start:
            for col in _ASSEMBLY_CHANGE_ORDER_COLS:
                _merge_vertical(sheet, col, first_row + start, first_row + end)
        start = end + 1


def _merge_vertical(sheet: Worksheet, col: int, start_row: int, end_row: int) -> None:
    if end_row > start_row:
        sheet.merge_cells(
            start_row=start_row,
            start_column=col,
            end_row=end_row,
            end_column=col,
        )


CHANGE_ORDER_SAMPLES = (
    ChangeOrderSample(
        CHANGE_TYPE_STOP,
        "EX-STOP-AA",
        None,
        "示例总成（完成停止）",
        PART_LEVEL_ASSEMBLY,
        None,
        None,
        None,
    ),
    ChangeOrderSample(
        CHANGE_TYPE_REVISE,
        "EX-L1-AA",
        "EX-L1-AB",
        "示例总成（改图一级）",
        PART_LEVEL_L1,
        "EX-L1-PART-AA",
        "EX-L1-PART-AB",
        "示例零件（改图一级）",
    ),
    ChangeOrderSample(
        CHANGE_TYPE_REVISE,
        "EX-L2-AA",
        "EX-L2-AB",
        "示例总成（改图二级）",
        PART_LEVEL_L2,
        "EX-L2-PART-AA",
        "EX-L2-PART-AB",
        "示例零件（改图二级）",
    ),
    ChangeOrderSample(
        CHANGE_TYPE_NOT_INSTALL,
        "EX-SKIP-AA",
        "EX-SKIP-AB",
        "示例总成（此件不装）",
        PART_LEVEL_L1,
        "EX-SKIP-PART-AA",
        None,
        "示例零件（此件不装）",
    ),
    ChangeOrderSample(
        CHANGE_TYPE_ADD_PART,
        "EX-ADD-AA",
        "EX-ADD-AB",
        "示例总成（增加零件）",
        PART_LEVEL_L1,
        None,
        ADD_PART_NUMBER,
        "示例零件（增加零件）",
    ),
    ChangeOrderSample(
        CHANGE_TYPE_ADD_SUBASSEMBLY,
        LEAF_BEFORE,
        LEAF_AFTER,
        "示例总成（增加分总成）",
        PART_LEVEL_L1,
        None,
        LEAF_SUB,
        "示例分总成",
    ),
)

BOM_SAMPLES = (
    BomSample(
        seq_no=1,
        internal_number="EX610",
        part_number="EX-L1-AB",
        part_name="示例总成（改图一级）",
        weld_info="焊点：4",
        l1_internal="EX610001",
        l1_part_number="EX-L1-PART-AB",
        l1_part_name="示例零件（改图一级）",
        l1_qty="1",
        l1_weld=SLASH,
        l2_internal=SLASH,
        l2_part_number=SLASH,
        l2_part_name=SLASH,
        l2_qty=SLASH,
        material="DC01",
        thickness_text="T=1.0",
        part_weight=0.1,
        gauge_developed="是",
        remark=None,
    ),
    BomSample(
        seq_no=2,
        internal_number="EX611",
        part_number="EX-SKIP-AB",
        part_name="示例总成（此件不装）",
        weld_info=SLASH,
        l1_internal="EX611001",
        l1_part_number="EX-SKIP-PART-AA",
        l1_part_name="示例零件（此件不装）",
        l1_qty=0,
        l1_weld=SLASH,
        l2_internal=SLASH,
        l2_part_number=SLASH,
        l2_part_name=SLASH,
        l2_qty=SLASH,
        material=SLASH,
        thickness_text=SLASH,
        part_weight=0.1,
        gauge_developed="否",
        remark=CHANGE_TYPE_NOT_INSTALL,
        is_not_assembled=True,
    ),
    BomSample(
        seq_no=3,
        internal_number="EX612",
        part_number="EX-L2-AB",
        part_name="示例总成（改图二级）",
        weld_info="焊缝：1条",
        l1_internal="EX612N01",
        l1_part_number="EX-L2-SUB-AB",
        l1_part_name="示例分总成（改图二级）",
        l1_qty="1",
        l1_weld="凸焊:1",
        l2_internal=SLASH,
        l2_part_number="EX-L2-PART-AB",
        l2_part_name="示例零件（改图二级）",
        l2_qty="1",
        material="DC01",
        thickness_text="T=1.0",
        part_weight=0.1,
        gauge_developed="是",
        remark=None,
    ),
    BomSample(
        seq_no=4,
        internal_number="EX613",
        part_number="EX-ADD-AB",
        part_name="示例总成（增加零件）",
        weld_info="焊点：1",
        l1_internal="EX613001",
        l1_part_number=ADD_PART_NUMBER,
        l1_part_name="示例零件（增加零件）",
        l1_qty="1",
        l1_weld=SLASH,
        l2_internal=SLASH,
        l2_part_number=SLASH,
        l2_part_name=SLASH,
        l2_qty=SLASH,
        material="DC01",
        thickness_text="T=1.0",
        part_weight=0.1,
        gauge_developed=SLASH,
        remark=None,
        is_added_part=True,
    ),
    BomSample(
        seq_no=5,
        internal_number="EX615",
        part_number=LEAF_AFTER,
        part_name="示例总成（增加分总成）",
        weld_info="焊点：1",
        l1_internal="EX615N01",
        l1_part_number=LEAF_SUB,
        l1_part_name="示例分总成",
        l1_qty="1",
        l1_weld=SLASH,
        l2_internal="EX615002",
        l2_part_number=LEAF_ADD,
        l2_part_name="示例零件（新冲压件）",
        l2_qty="1",
        material="DC01",
        thickness_text="T=1.0",
        part_weight=0.1,
        gauge_developed=SLASH,
        remark=None,
        is_added_part=True,
        part_sketch=True,
    ),
    BomSample(
        seq_no=5,
        internal_number="",
        part_number="",
        part_name="",
        weld_info="",
        l1_internal="",
        l1_part_number="",
        l1_part_name="",
        l1_qty="",
        l1_weld="",
        l2_internal="EX615003",
        l2_part_number=LEAF_NUT,
        l2_part_name="示例螺母",
        l2_qty="2",
        material=SLASH,
        thickness_text=SLASH,
        part_weight=0.01,
        gauge_developed=SLASH,
        remark=None,
        is_added_part=True,
        blank_assembly=True,
        blank_l1=True,
        part_sketch=True,
        group_part_number=LEAF_AFTER,
    ),
)

PROCESS_SAMPLES = (
    ProcessSample(
        "EX-L1-PART-AB",
        "示例零件（改图一级）",
        "DC01",
        1.0,
        0.1,
        100,
        80,
        1,
        "卷料",
        "OP10",
        "PRG",
        1,
        250,
        "钢板模",
    ),
    ProcessSample(
        "EX-L2-PART-AB",
        "示例零件（改图二级）",
        "DC01",
        1.0,
        0.1,
        100,
        80,
        1,
        "卷料",
        "OP10",
        "PRG",
        1,
        250,
        "钢板模",
    ),
    ProcessSample(
        ADD_PART_NUMBER,
        "示例零件（增加零件）",
        "DC01",
        1.0,
        0.1,
        100,
        80,
        1,
        "卷料",
        "OP10",
        "PRG",
        1,
        250,
        "钢板模",
    ),
    ProcessSample(
        LEAF_ADD,
        "示例零件（新冲压件）",
        "DC01",
        1.0,
        0.1,
        100,
        80,
        1,
        "卷料",
        "OP10",
        "PRG",
        1,
        250,
        "钢板模",
    ),
)


def _fill_note(meta: TemplateMeta, change_type: str | None = None) -> str:
    """变更单说明。整本和单种改法共用这一段，只换开头。"""
    if change_type:
        opening = f"{meta.location} {meta.vehicle_model} 一种改法举例：{change_type}。"
    else:
        opening = (
            f"{meta.location} {meta.vehicle_model} 五种改法举例，一行一个交货总成。"
            f"{CHANGE_TYPE_ADD_SUBASSEMBLY}是一套一级节点，下面至少两颗二级。"
        )
    return (
        opening + "零件号是例子，请改成这个项目自己的零件号后再上传。"
        f"基地 {meta.location}，项目 {meta.vehicle_model}，顾客 {meta.customer_name}，"
        f"生效 {meta.period_label}，投产清单版本 {meta.bom_version_label}。"
        f"五种改法：{CHANGE_TYPE_STOP} / {CHANGE_TYPE_REVISE} / {CHANGE_TYPE_ADD_PART} / "
        f"{CHANGE_TYPE_NOT_INSTALL} / {CHANGE_TYPE_ADD_SUBASSEMBLY}。"
        f"{CHANGE_TYPE_REVISE}按末级所在层级写一级或二级，各举一行。"
        "同一个总成改了好几处，请把变更前总成、变更后总成格子上下合并；完成停止不用填变更后总成。"
        "先写原来的交货总成，再写变更类型和这一次动到的零件。"
        "材料清单只写变化的行；改图二级写出整条链。没变的零件不要抄。"
        f"{CHANGE_TYPE_STOP}：变更后总成空，材料清单不写这个总成。"
        f"{CHANGE_TYPE_NOT_INSTALL}：变更后零件空；用量 0、备注含「{CHANGE_TYPE_NOT_INSTALL}」。"
        f"{CHANGE_TYPE_ADD_PART}：加在原来的总成上；变更前零件空、变更后零件写新号。"
        f"{CHANGE_TYPE_ADD_SUBASSEMBLY}：增加一套一级节点。变更后零件是新的一级分总成号。"
        "一套同时有这一级，和它下面的二级；二级至少两颗。只有一颗二级，整份不收。"
        "样表这一级下面是一颗冲压件和一颗螺母。"
        f"{CHANGE_TYPE_NOT_INSTALL}另写一行，不和这一套核对。"
        "已经有二级的一级下面再加零件，上级一级换成新版本，旁边的二级仍是原号。"
        "一级下面原来没有二级，不能直接增加零件。"
        "材料清单和确认表项目号、版本都要对齐（版本写成同一个字）；"
        "先到焊接工程生成采购对象；生效月须在项目有效期内。细节看「设计变更填写说明」。"
    )


@dataclass(frozen=True, slots=True)
class ScenarioSample:
    filename: str
    book: TemplateBook


def _scenario_note(sample: ChangeOrderSample) -> str:
    return _fill_note(DEFAULT_META, sample.change_type)


def _part_numbers_on_bom(samples: tuple[BomSample, ...]) -> set[str]:
    numbers: set[str] = set()
    for sample in samples:
        for number in (sample.part_number, sample.l1_part_number, sample.l2_part_number):
            if number and number != SLASH:
                numbers.add(number)
    return numbers


def _book_for_change_order(sample: ChangeOrderSample) -> TemplateBook:
    after_assembly = sample.after_assembly
    bom = (
        tuple(
            item
            for item in BOM_SAMPLES
            if (item.group_part_number or item.part_number) == after_assembly
        )
        if after_assembly
        else ()
    )
    bom_numbers = _part_numbers_on_bom(bom)
    process = tuple(item for item in PROCESS_SAMPLES if item.part_number in bom_numbers)
    return TemplateBook(
        change_orders=(sample,),
        bom=bom,
        process=process,
        change_order_note=_scenario_note(sample),
        meta=DEFAULT_META,
    )


SCENARIO_FILENAMES = (
    "example-stop.xlsx",
    "example-rev-l1.xlsx",
    "example-rev-l2.xlsx",
    "example-not-install.xlsx",
    "example-add-part.xlsx",
    "example-add-subassembly.xlsx",
)

SCENARIO_SAMPLES = tuple(
    ScenarioSample(filename=filename, book=_book_for_change_order(sample))
    for filename, sample in zip(SCENARIO_FILENAMES, CHANGE_ORDER_SAMPLES, strict=True)
)

_ASSEMBLY_SKETCH_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x00\x03\x00\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def example_book(meta: TemplateMeta) -> TemplateBook:
    """按所选基地、项目写整本举例。零件号与不传 book 时是同一套。"""
    return TemplateBook(
        change_orders=CHANGE_ORDER_SAMPLES,
        bom=BOM_SAMPLES,
        process=PROCESS_SAMPLES,
        change_order_note=_fill_note(meta),
        meta=meta,
    )


COMBINED_BOOK = example_book(DEFAULT_META)


def build_engineering_change_template(
    book: TemplateBook | None = None,
) -> tuple[bytes, str]:
    """不传 book 时用默认抬头和同一套举例零件。下载按所选项目另传 book。"""
    samples = book or COMBINED_BOOK
    meta = samples.meta
    dest_wb = Workbook()
    order_sheet = dest_wb.active
    assert order_sheet is not None
    order_sheet.title = SHEET_CHANGE_ORDER
    _write_change_order(order_sheet, samples.change_orders, samples.change_order_note, meta)
    _write_ec_fill_instructions(dest_wb.create_sheet(SHEET_CHANGE_ORDER_HINT, 1), meta)
    filename = TEMPLATE_FILENAME
    if meta != DEFAULT_META:
        filename = f"设计变更导入模板_{meta.location}_{meta.vehicle_model}.xlsx"

    bom_wb = load_workbook(BytesIO(build_bom_material_template()[0]))
    bom_sheet = _copy_sheet(bom_wb["车身件材料清单"], dest_wb, "车身件材料清单")
    _write_bom_header(bom_sheet, meta)
    _clear_row_range(bom_sheet, 5, 200, 23)
    for offset, bom_sample in enumerate(samples.bom):
        _write_bom_row(bom_sheet, 5 + offset, bom_sample)
    _copy_sheet(bom_wb["填写说明"], dest_wb, "材料清单填写说明")

    process_wb = load_workbook(BytesIO(build_stamping_process_template()[0]))
    process_sheet = _copy_sheet(process_wb["冲压工艺确认表"], dest_wb, "冲压工艺确认表")
    _strip_process_sample(process_sheet, meta)
    process_row = 7
    process_sketch_rows: list[int] = []
    for seq_no, process_group in _grouped_process_parts(samples.process):
        process_sketch_rows.append(process_row)
        process_row = _fill_process_part(
            process_sheet,
            process_group,
            start_row=process_row,
            seq_no=seq_no,
        )
    _copy_sheet(process_wb["填写说明"], dest_wb, "工艺确认填写说明")

    buffer = BytesIO()
    with TemporaryDirectory() as temp_dir:
        png_path = Path(temp_dir) / "assembly.png"
        png_path.write_bytes(_ASSEMBLY_SKETCH_PNG)
        _embed_assembly_sketches(bom_sheet, samples.bom, png_path)
        _embed_part_sketches(
            bom_sheet,
            _part_sketch_rows(samples.bom),
            png_path,
            file_prefix="bom_l1",
            anchor_column="P",
        )
        _embed_part_sketches(
            process_sheet, process_sketch_rows, png_path, file_prefix="process", anchor_column="D"
        )
        dest_wb.save(buffer)
    return buffer.getvalue(), filename


def _write_change_order(
    sheet: Worksheet,
    change_orders: tuple[ChangeOrderSample, ...],
    change_order_note: str,
    meta: TemplateMeta,
) -> None:
    title = Font(name="微软雅黑", size=14, bold=True)
    label = Font(name="微软雅黑", size=10)
    head = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="4472C4")
    sheet["A1"] = SHEET_CHANGE_ORDER
    sheet["A1"].font = title
    sheet.merge_cells("A1:J1")
    sheet["A2"] = change_order_note
    sheet["A2"].font = Font(name="微软雅黑", size=9, color="666666")
    sheet["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    sheet.merge_cells("A2:J2")
    sheet.row_dimensions[2].height = 210
    for col, header in enumerate(CHANGE_ORDER_HEADERS, start=1):
        cell = sheet.cell(4, col, header)
        cell.font = head
        cell.fill = fill
        cell.border = _THIN
        cell.alignment = _CENTER
    for offset, sample in enumerate(change_orders):
        excel_row = 5 + offset
        values = (
            meta.vehicle_model,
            meta.period_label,
            sample.before_assembly,
            sample.after_assembly or "",
            sample.assembly_name,
            sample.change_type,
            sample.part_level,
            sample.before_part or "",
            sample.after_part or "",
            sample.part_name or "",
        )
        for col, value in enumerate(values, start=1):
            cell = sheet.cell(excel_row, col, value)
            cell.font = label
            cell.border = _THIN
            cell.alignment = _CENTER
            if col == 2:
                _write_effective_period(cell, meta.period_label)
            if col in {6, 7, 8, 9, 10}:
                if sample.change_type == CHANGE_TYPE_NOT_INSTALL:
                    cell.fill = _NOT_ASSEMBLED_FILL
                if sample.change_type in {CHANGE_TYPE_ADD_PART, CHANGE_TYPE_ADD_SUBASSEMBLY}:
                    cell.fill = _ADD_PART_FILL
        sheet.row_dimensions[excel_row].height = 28
    last_change_order_row = 4 + len(change_orders)
    if last_change_order_row > 5:
        sheet.merge_cells(f"A5:A{last_change_order_row}")
        sheet.merge_cells(f"B5:B{last_change_order_row}")
    _merge_same_assembly_change_order_rows(sheet, change_orders, 5)
    widths = (12, 14, 22, 22, 28, 12, 10, 22, 22, 28)
    for col, width in enumerate(widths, start=1):
        sheet.column_dimensions[chr(64 + col)].width = width
    sheet.freeze_panes = "A5"


class _CellStyleHolder(Protocol):
    _style: StyleArray | None


def _write_effective_period(cell: Cell, period_label: str) -> None:
    """生效年月写成 Excel 日期，格式为中文年月。"""
    match = _PERIOD_LABEL_RE.match(period_label.strip())
    if match is None:
        return
    year = int(match.group(1))
    month = int(match.group(2))
    cell.value = (datetime(year, month, 1) - _EXCEL_EPOCH).days
    holder = cast(_CellStyleHolder, cell)
    if holder._style is None:
        holder._style = StyleArray()
    holder._style.numFmtId = _EXCEL_YEAR_MONTH_FORMAT_ID


def _write_ec_fill_instructions(sheet: Worksheet, meta: TemplateMeta) -> None:
    sheet["A1"] = SHEET_CHANGE_ORDER_HINT
    sheet["A1"].font = Font(name="微软雅黑", size=14, bold=True)
    lines = (
        "上传页不填版本。车身件材料清单第 2 行「版本：」必填；冲压工艺确认表表头「版本」必填。"
        f"两张表必须写成同一个字（样表都是 {meta.change_version}）。任一张空、或两张写成不一样，整单不能导入。"
        f"设变后的总成、工艺、布点都用这个字，不会改成投产清单的 {meta.bom_version_label}，也不会各用各的。布点不要另填表。",
        "一本只能一个项目号。系统会拆：材料清单第 3 行「项目代号」、确认表标题"
        "「某某项目冲压工艺确认表」里「项目」前面那一段（或表头项目名称）。"
        "必须和上传页、设计变更单同一项目。拆不出或对不上，整单不能导入。",
        "上传前，该基地+项目须已在「焊接工程 → 采购对象」生成过清单。没有清单则拒收；系统不代建空清单。",
        "完成停止：材料清单不要写这个总成；确认表可以空表体。项目号仍要对齐；"
        "两张表头「版本」仍必须同一字且非空。没有「只建议、不拦截」。",
        "先自洽：确认表上的零件号、变更单上的变更后零件，都必须写在材料清单里。"
        "对不上时系统一次列出缺哪些号，请改表后再传。",
        "变更生效月必须在该项目有效期内。早于项目开始或晚于项目结束，整单不能导入。完成停止同样。",
        "增加分总成：增加一套一级节点。变更后零件写新的一级分总成号，层级写一级。"
        "一套同时有这一级，和它下面的二级；二级至少两颗。只有一颗二级，整份不收。"
        "样表这一级下面是一颗冲压件和一颗螺母。"
        "此件不装仍按原来的停用另写，不和这一套核对。"
        "增加零件时，上级一级下面原来没有二级，整份不收。",
    )
    sheet.merge_cells("A1:F1")
    for index, line in enumerate(lines, start=2):
        cell = sheet.cell(index, 1, f"{index - 1}. {line}")
        cell.font = Font(name="微软雅黑", size=10)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        sheet.merge_cells(start_row=index, start_column=1, end_row=index, end_column=6)
        sheet.row_dimensions[index].height = 48
    sheet.column_dimensions["A"].width = 28
    for col in ("B", "C", "D", "E", "F"):
        sheet.column_dimensions[col].width = 18


def _write_bom_header(sheet: Worksheet, meta: TemplateMeta) -> None:
    sheet["A1"] = f"{meta.vehicle_model}项目产品材料清单"
    sheet["A2"] = (
        "编制部门： 技术中心                    "
        f"编制日期：{meta.header_date}  版本： {meta.change_version}  "
        f"编号：{meta.doc_no}"
    )
    sheet["A3"] = f"项目代号：  {meta.vehicle_model}"
    sheet["I3"] = "产品类别：  车身件"
    sheet["N3"] = f"顾客名称：  {meta.customer_name}"
    sheet["P3"] = "阶段标识： D"
    sheet["R3"] = "■批量生产清单"
    sheet["V3"] = f"修订日期：{meta.header_date}"


def _write_bom_row(sheet: Worksheet, row: int, sample: BomSample) -> None:
    fill = None
    if sample.is_not_assembled:
        fill = _NOT_ASSEMBLED_FILL
    elif sample.is_added_part:
        fill = _ADD_PART_FILL
    for col in range(1, 24):
        cell = sheet.cell(row, col)
        cell.font = _DATA_FONT
        cell.border = _THIN
        cell.alignment = _CENTER
        if fill is not None:
            cell.fill = fill
    sheet.row_dimensions[row].height = 22
    if not sample.blank_assembly:
        sheet.cell(row, 1, sample.seq_no)
        sheet.cell(row, 2, sample.internal_number)
        sheet.cell(row, 3, sample.part_number)
        sheet.cell(row, 4, sample.part_name)
        sheet.cell(row, 6, 1)
        sheet.cell(row, 7, sample.weld_info)
    if not sample.blank_l1:
        sheet.cell(row, 8, sample.l1_internal)
        sheet.cell(row, 9, sample.l1_part_number)
        sheet.cell(row, 10, sample.l1_part_name)
        sheet.cell(row, 11, sample.l1_qty)
        sheet.cell(row, 12, sample.l1_weld)
    sheet.cell(row, 13, sample.l2_internal)
    sheet.cell(row, 14, sample.l2_part_number)
    sheet.cell(row, 15, sample.l2_part_name)
    sheet.cell(row, 17, sample.l2_qty)
    sheet.cell(row, 18, sample.material)
    sheet.cell(row, 19, sample.thickness_text)
    sheet.cell(row, 21, sample.part_weight)
    sheet.cell(row, 22, sample.gauge_developed)
    sheet.cell(row, 23, sample.remark)


def _part_sketch_rows(samples: tuple[BomSample, ...]) -> list[int]:
    """一级叶子贴 P 列。新分总成那一行已经写了二级，单件图示要单独点名。"""
    rows = _l1_part_sketch_rows(samples)
    for offset, sample in enumerate(samples):
        excel_row = 5 + offset
        if sample.part_sketch and excel_row not in rows:
            rows.append(excel_row)
    return rows


def _l1_part_sketch_rows(samples: tuple[BomSample, ...]) -> list[int]:
    """一级叶子（无二级、非此件不装）在 P 列贴单件图示。"""
    rows: list[int] = []
    for offset, sample in enumerate(samples):
        if sample.is_not_assembled:
            continue
        if sample.l2_part_number and sample.l2_part_number != SLASH:
            continue
        rows.append(5 + offset)
    return rows


def _embed_assembly_sketches(
    sheet: Worksheet, samples: tuple[BomSample, ...], png_path: Path
) -> None:
    seen: set[str] = set()
    for offset, sample in enumerate(samples):
        if not sample.part_number or sample.part_number in seen:
            continue
        seen.add(sample.part_number)
        copy_path = png_path.parent / f"assembly_{offset}.png"
        copy_path.write_bytes(png_path.read_bytes())
        image = ExcelImage(str(copy_path))
        image.width = 36
        image.height = 36
        sheet.add_image(image, f"E{5 + offset}")


def _embed_part_sketches(
    sheet: Worksheet,
    start_rows: list[int],
    png_path: Path,
    *,
    file_prefix: str,
    anchor_column: str,
) -> None:
    for index, start_row in enumerate(start_rows):
        copy_path = png_path.parent / f"{file_prefix}_{index}.png"
        copy_path.write_bytes(png_path.read_bytes())
        image = ExcelImage(str(copy_path))
        image.width = 36
        image.height = 36
        sheet.add_image(image, f"{anchor_column}{start_row}")


def _strip_process_sample(sheet: Worksheet, meta: TemplateMeta) -> None:
    sheet["D2"] = f"{meta.vehicle_model}项目冲压工艺确认表-设计变更"
    sheet["D3"] = meta.stamping_supplier
    sheet["S3"] = meta.change_version
    sheet.column_dimensions["D"].width = 14
    max_row = sheet.max_row or 6
    _clear_row_range(sheet, 7, max(max_row, 7), 20)


def _fill_process_part(
    sheet: Worksheet,
    samples: tuple[ProcessSample, ...],
    *,
    start_row: int,
    seq_no: int,
) -> int:
    first = samples[0]
    end_row = start_row + len(samples) - 1
    for excel_row in range(start_row, end_row + 1):
        for col in range(1, 20):
            cell = sheet.cell(excel_row, col)
            cell.border = _THIN
            cell.font = _DATA_FONT
            cell.alignment = _CENTER
        sheet.row_dimensions[excel_row].height = 36
    for col in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 19):
        _merge_vertical(sheet, col, start_row, end_row)
    sheet.cell(start_row, 1, seq_no)
    sheet.cell(start_row, 2, first.part_number)
    sheet.cell(start_row, 3, first.part_name)
    sheet.cell(start_row, 5, first.material)
    sheet.cell(start_row, 6, first.thickness)
    sheet.cell(start_row, 7, first.part_weight)
    sheet.cell(start_row, 8, first.sheet_length)
    sheet.cell(start_row, 9, first.sheet_width)
    sheet.cell(start_row, 10, first.parts_per_sheet)
    sheet.cell(start_row, 13, first.sheet_type)
    sheet.cell(start_row, 19, first.die_type)
    for offset, sample in enumerate(samples):
        excel_row = start_row + offset
        sheet.cell(excel_row, 14, sample.process_seq)
        sheet.cell(excel_row, 15, sample.process_code)
        sheet.cell(excel_row, 16, sample.die_sets)
        sheet.cell(excel_row, 18, sample.tonnage)
    return end_row + 1


def _unmerge_in_rows(sheet: Worksheet, min_row: int, max_row: int) -> None:
    ranges = [
        str(item)
        for item in sheet.merged_cells.ranges
        if item.min_row >= min_row and item.max_row <= max_row
    ]
    for item in ranges:
        sheet.unmerge_cells(item)


def _clear_row_range(sheet: Worksheet, start_row: int, end_row: int, max_col: int) -> None:
    _unmerge_in_rows(sheet, start_row, end_row)
    for row in range(start_row, end_row + 1):
        for col in range(1, max_col + 1):
            sheet.cell(row, col).value = None


def _copy_sheet(source: Worksheet, dest_wb: Workbook, title: str) -> Worksheet:
    dest = cast(Worksheet, dest_wb.create_sheet(title))
    for row in source.iter_rows():
        for cell in row:
            cloned = dest.cell(cell.row, cell.column, cell.value)
            if cell.has_style:
                cloned.font = copy(cell.font)
                cloned.border = copy(cell.border)
                cloned.fill = copy(cell.fill)
                cloned.number_format = cell.number_format
                cloned.protection = copy(cell.protection)
                cloned.alignment = copy(cell.alignment)
    for merged in source.merged_cells.ranges:
        dest.merge_cells(str(merged))
    for letter, col_dim in source.column_dimensions.items():
        dest.column_dimensions[letter].width = col_dim.width
    for index, row_dim in source.row_dimensions.items():
        dest.row_dimensions[index].height = row_dim.height
    dest.freeze_panes = source.freeze_panes
    dest.sheet_view.zoomScale = source.sheet_view.zoomScale or 100
    dest.print_title_rows = source.print_title_rows
    dest.print_area = source.print_area
    return dest
