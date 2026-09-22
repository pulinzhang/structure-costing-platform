"""写出芜湖 T13J · 2025年05月工程变更导入样表：对照一本 + 五种改法各一份。"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from app.common.engineering_change_gates import (  # noqa: E402
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    PART_LEVEL_ASSEMBLY,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
)
from app.services.engineering_change.design_change.upload.template_builder import (  # noqa: E402
    BomSample,
    ChangeOrderSample,
    ProcessSample,
    ScenarioSample,
    TemplateBook,
    TemplateMeta,
    build_engineering_change_template,
)

SAMPLES = Path(__file__).resolve().parent
COMBINED_OUT = SAMPLES / "t13j-2025-05-import-bundle.xlsx"
SLASH = "/"
ADD_PART_NUMBER = "501012540AA"

META = TemplateMeta(
    location="芜湖",
    vehicle_model="T13J",
    customer_name="奇瑞公司",
    period_label="2025年05月",
    change_version="EC-202505",
    stamping_supplier="安徽振华汽车部件有限责任公司",
    bom_version_label="D/09",
    header_date="2025-05-01",
    doc_no="EC-T13J-202505",
)

CHANGE_ORDER_SAMPLES = (
    ChangeOrderSample(
        CHANGE_TYPE_STOP,
        "553000999AA",
        None,
        "发盖左铰链加强板总成",
        PART_LEVEL_ASSEMBLY,
        None,
        None,
        None,
    ),
    ChangeOrderSample(
        CHANGE_TYPE_REVISE,
        "551003085AA",
        "551003085AB",
        "左前门上铰链加强板总成",
        PART_LEVEL_L1,
        "551003095AA",
        "551003095AB",
        "左前门上铰链加强板",
    ),
    ChangeOrderSample(
        CHANGE_TYPE_REVISE,
        "502007390AA",
        "502007390AB",
        "左后尾灯安装板总成",
        PART_LEVEL_L2,
        "502007710AA",
        "502007710AB",
        "左后尾灯安装板",
    ),
    ChangeOrderSample(
        CHANGE_TYPE_NOT_INSTALL,
        "502007395AB",
        "502007395AC",
        "左侧围内板前部总成",
        PART_LEVEL_L1,
        "504000714AA",
        None,
        "左B柱结构增强胶块",
    ),
    ChangeOrderSample(
        CHANGE_TYPE_ADD_PART,
        "501012534AA",
        "501012534AB",
        "左前翼子板前安装支架总成",
        PART_LEVEL_L1,
        None,
        ADD_PART_NUMBER,
        "左前翼子板前安装支架加强板",
    ),
)

BOM_SAMPLES = (
    BomSample(
        seq_no=4,
        internal_number="ACA673",
        part_number="551003085AB",
        part_name="左前门上铰链加强板总成",
        weld_info="焊点：4 凸焊：1",
        l1_internal="ACA673001",
        l1_part_number="551003095AB",
        l1_part_name="左前门上铰链加强板",
        l1_qty="1",
        l1_weld=SLASH,
        l2_internal=SLASH,
        l2_part_number=SLASH,
        l2_part_name=SLASH,
        l2_qty=SLASH,
        material="HC340/590DPD+Z",
        thickness_text="T=1.5",
        part_weight=0.558,
        gauge_developed="是",
        remark=None,
    ),
    BomSample(
        seq_no=13,
        internal_number="ACA682",
        part_number="502007390AB",
        part_name="左后尾灯安装板总成",
        weld_info="凸焊：2 焊点：10 涂胶：255mm",
        l1_internal="ACA682N01",
        l1_part_number="502007710AB-1",
        l1_part_name="左后尾灯安装板分总成",
        l1_qty="1",
        l1_weld="凸焊:1",
        l2_internal="ACA682002",
        l2_part_number="502007710AB",
        l2_part_name="左后尾灯安装板",
        l2_qty="1",
        material="DC56D+Z",
        thickness_text="T=0.65",
        part_weight=0.383,
        gauge_developed="是",
        remark=None,
    ),
    BomSample(
        seq_no=35,
        internal_number="CA0008",
        part_number="502007395AC",
        part_name="左侧围内板前部总成",
        weld_info="焊点：83 凸焊：13 涂胶：195mm",
        l1_internal="ACA710001",
        l1_part_number="504000714AA",
        l1_part_name="左B柱结构增强胶块",
        l1_qty=0,
        l1_weld=SLASH,
        l2_internal=SLASH,
        l2_part_number=SLASH,
        l2_part_name=SLASH,
        l2_qty=SLASH,
        material="PA6+聚氨酯",
        thickness_text=SLASH,
        part_weight=0.19,
        gauge_developed="否",
        remark=CHANGE_TYPE_NOT_INSTALL,
        is_not_assembled=True,
    ),
    BomSample(
        seq_no=15,
        internal_number="ACA689",
        part_number="501012534AB",
        part_name="左前翼子板前安装支架总成",
        weld_info="凸焊：2",
        l1_internal="ACA689002",
        l1_part_number=ADD_PART_NUMBER,
        l1_part_name="左前翼子板前安装支架加强板",
        l1_qty="1",
        l1_weld=SLASH,
        l2_internal=SLASH,
        l2_part_number=SLASH,
        l2_part_name=SLASH,
        l2_qty=SLASH,
        material="HC180YD+Z",
        thickness_text="T=1.5",
        part_weight=0.126,
        gauge_developed=SLASH,
        remark=None,
        is_added_part=True,
    ),
)


def _process_rows(
    part_number: str,
    part_name: str,
    material: str,
    thickness: float,
    part_weight: float,
    sheet_length: int,
    sheet_width: int,
    parts_per_sheet: int,
    sheet_type: str,
    die_type: str,
    ops: tuple[tuple[str, str, int | None], ...],
) -> tuple[ProcessSample, ...]:
    return tuple(
        ProcessSample(
            part_number,
            part_name,
            material,
            thickness,
            part_weight,
            sheet_length,
            sheet_width,
            parts_per_sheet,
            sheet_type,
            process_seq,
            process_code,
            1,
            tonnage,
            die_type,
        )
        for process_seq, process_code, tonnage in ops
    )


PROCESS_SAMPLES = (
    *_process_rows(
        "551003095AB",
        "左前门上铰链加强板",
        "HC340/590DPD+Z",
        1.5,
        0.558,
        625,
        240,
        2,
        "方料",
        "铸造模",
        (
            ("OP10", "DR", 630),
            ("OP20", "TR+CTR+PI", 400),
            ("OP30", "RST+UP FL", 400),
            ("OP40", "TR+PI", 400),
            ("OP50", "SEP+PI", 400),
        ),
    ),
    *_process_rows(
        "502007710AB",
        "左后尾灯安装板",
        "DC56D+Z",
        0.65,
        0.383,
        515,
        370,
        1,
        "方料",
        "铸造模",
        (
            ("OP10", "DR+CUT", 800),
            ("OP20", "TR+CTR+PI", 630),
            ("OP30", "TR+CTR+PI", 400),
            ("OP40", "FL(UP)+RST(UP)+RST", 630),
            ("OP50", "CTR+PI", 400),
        ),
    ),
    *_process_rows(
        ADD_PART_NUMBER,
        "左前翼子板前安装支架加强板",
        "HC180YD+Z",
        1.5,
        0.126,
        1195,
        148,
        11,
        "方料",
        "钢板模",
        (
            ("OP05", "BL+PI", 80),
            ("OP10", "FO+FL", 160),
            ("OP20", "FL", 160),
            ("OP30", "PI+CPI", 160),
            ("OP40", "CPI", 160),
        ),
    ),
)

COMBINED_NOTE = (
    "芜湖 T13J 五种改法，一行一个交货总成，可直接上传。"
    f"基地 {META.location}，顾客 {META.customer_name}，投产清单版本 {META.bom_version_label}。"
    f"五行：{CHANGE_TYPE_STOP} / 一级{CHANGE_TYPE_REVISE} / 二级{CHANGE_TYPE_REVISE} / "
    f"{CHANGE_TYPE_NOT_INSTALL} / {CHANGE_TYPE_ADD_PART}。"
    "同一个总成改了好几处，请把变更前总成、变更后总成格子上下合并；完成停止不用填变更后总成。"
    "先写原来的交货总成，再写变更类型和这一次动到的零件。"
    "材料清单只写变化的行；改图二级写出整条链。没变的零件不要抄。"
    f"{CHANGE_TYPE_STOP}：变更后总成空，材料清单不写这个总成。"
    f"{CHANGE_TYPE_NOT_INSTALL}：变更后零件空；用量 0、备注含「{CHANGE_TYPE_NOT_INSTALL}」。"
    f"{CHANGE_TYPE_ADD_PART}：加在原来的总成上；变更前零件空、变更后零件写新号。"
)

COMBINED_BOOK = TemplateBook(
    change_orders=CHANGE_ORDER_SAMPLES,
    bom=BOM_SAMPLES,
    process=PROCESS_SAMPLES,
    change_order_note=COMBINED_NOTE,
    meta=META,
)

SCENARIO_FILENAMES = (
    "t13j-2025-05-stop.xlsx",
    "t13j-2025-05-rev-l1.xlsx",
    "t13j-2025-05-rev-l2.xlsx",
    "t13j-2025-05-not-install.xlsx",
    "t13j-2025-05-add-part.xlsx",
)


def _scenario_note(sample: ChangeOrderSample) -> str:
    after_assembly = sample.after_assembly or "空"
    return (
        f"芜湖 T13J 单种改法：{sample.change_type}。"
        f"基地 {META.location}，顾客 {META.customer_name}，"
        f"投产清单版本 {META.bom_version_label}。"
        f"变更前总成 {sample.before_assembly}，变更后总成 {after_assembly}。"
        "材料清单只写变化的行；改图二级写出整条链。没变的零件不要抄。"
        f"{CHANGE_TYPE_STOP}：变更后总成空，材料清单不写这个总成。"
        f"{CHANGE_TYPE_NOT_INSTALL}：变更后零件空；用量 0、备注含「{CHANGE_TYPE_NOT_INSTALL}」。"
        f"{CHANGE_TYPE_ADD_PART}：加在原来的总成上；变更前零件空、变更后零件写新号。"
    )


def _book_for_change_order(sample: ChangeOrderSample) -> TemplateBook:
    after_assembly = sample.after_assembly
    bom = (
        tuple(item for item in BOM_SAMPLES if item.part_number == after_assembly)
        if after_assembly
        else ()
    )
    after_part = sample.after_part
    process = (
        tuple(item for item in PROCESS_SAMPLES if item.part_number == after_part)
        if after_part
        else ()
    )
    return TemplateBook(
        change_orders=(sample,),
        bom=bom,
        process=process,
        change_order_note=_scenario_note(sample),
        meta=META,
    )


SCENARIO_SAMPLES = tuple(
    ScenarioSample(filename=filename, book=_book_for_change_order(sample))
    for filename, sample in zip(SCENARIO_FILENAMES, CHANGE_ORDER_SAMPLES, strict=True)
)


def _write_xlsx(path: Path, content: bytes) -> Path:
    temp_out = path.with_suffix(".building.xlsx")
    temp_out.write_bytes(content)
    try:
        temp_out.replace(path)
        return path
    except OSError:
        print(f"目标文件被占用，已写出: {temp_out}")
        return temp_out


def _print_book(path: Path, book: TemplateBook) -> None:
    types = [sample.change_type for sample in book.change_orders]
    process_numbers = list(dict.fromkeys(sample.part_number for sample in book.process))
    print(path.name)
    print(f"  工程变更单 {types}")
    print(f"  工艺新号={process_numbers}")


def main() -> None:
    combined_content, _ = build_engineering_change_template(COMBINED_BOOK)
    combined_path = _write_xlsx(COMBINED_OUT, combined_content)
    _print_book(combined_path, COMBINED_BOOK)

    for scenario in SCENARIO_SAMPLES:
        scenario_content, _ = build_engineering_change_template(scenario.book)
        scenario_path = _write_xlsx(SAMPLES / scenario.filename, scenario_content)
        _print_book(scenario_path, scenario.book)


if __name__ == "__main__":
    main()
