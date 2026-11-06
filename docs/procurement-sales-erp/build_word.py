"""把建设方案和产品与开发合同导出为 Word。"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ORANGE = RGBColor(0xD0, 0x4A, 0x02)
INK = RGBColor(0x2D, 0x2D, 0x2D)
MUTED = RGBColor(0x6B, 0x6B, 0x6B)
DIM = RGBColor(0x8A, 0x8A, 0x8A)
ORANGE_HEX = "D04A02"
SAND_HEX = "F3EEE6"
LINE_HEX = "E6E0D6"
CREAM_HEX = "FFFFFF"
FONT_CN = "微软雅黑"
FONT_EN = "Arial"


def set_run_font(
    run,
    size: float,
    *,
    bold: bool = False,
    color: RGBColor = INK,
    latin: str = FONT_EN,
    east: str = FONT_CN,
) -> None:
    run.font.name = latin
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.italic = False
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    fonts.set(qn("w:ascii"), latin)
    fonts.set(qn("w:hAnsi"), latin)
    fonts.set(qn("w:cs"), latin)
    fonts.set(qn("w:eastAsia"), east)


def shade_cell(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def shade_paragraph(paragraph, color: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    p_pr.append(shd)


def set_cell_margins(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = OxmlElement("w:tcMar")
    for edge, value in (("top", "60"), ("left", "80"), ("bottom", "60"), ("right", "80")):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:w"), value)
        node.set(qn("w:type"), "dxa")
        margins.append(node)
    tc_pr.append(margins)


def set_cell_edges(cell, frame: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    old = tc_pr.find(qn("w:tcBorders"))
    if old is not None:
        tc_pr.remove(old)
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        element = OxmlElement(f"w:{edge}")
        if frame == "none" or (frame == "rule" and edge != "bottom"):
            element.set(qn("w:val"), "nil")
            element.set(qn("w:sz"), "0")
            element.set(qn("w:space"), "0")
            element.set(qn("w:color"), "auto")
        else:
            orange = frame == "rule" or (frame == "header" and edge == "bottom")
            element.set(qn("w:val"), "single")
            element.set(qn("w:sz"), "12" if orange else "4")
            element.set(qn("w:space"), "0")
            element.set(qn("w:color"), ORANGE_HEX if orange else LINE_HEX)
        borders.append(element)
    tc_pr.append(borders)


def set_cell_text(
    cell, text: str, *, header: bool = False, bold: bool = False, frame: str = "grid"
) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.paragraph_format.line_spacing = 1.08
    add_marked_runs(paragraph, text.strip(), 10, bold=header or bold, color=INK)
    if header:
        shade_cell(cell, SAND_HEX)
    set_cell_edges(cell, "header" if header else frame)
    set_cell_margins(cell)
    tc_pr = cell._tc.get_or_add_tcPr()
    v_align = OxmlElement("w:vAlign")
    v_align.set(qn("w:val"), "center")
    tc_pr.append(v_align)


def add_marked_runs(
    paragraph,
    text: str,
    size: float,
    *,
    bold: bool = False,
    color: RGBColor = INK,
) -> None:
    parts = re.split(r"(\*\*.+?\*\*)", text)
    for part in parts:
        if not part:
            continue
        is_bold = part.startswith("**") and part.endswith("**")
        content = part[2:-2] if is_bold else part
        run = paragraph.add_run(content)
        set_run_font(run, size, bold=bold or is_bold, color=color)


def add_page_number(paragraph) -> None:
    def field(name: str) -> None:
        start = OxmlElement("w:fldChar")
        start.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = f" {name} "
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        begin_run = paragraph.add_run()
        set_run_font(begin_run, 9, color=DIM)
        begin_run._r.append(start)
        text_run = paragraph.add_run()
        set_run_font(text_run, 9, color=DIM)
        text_run._r.append(instr)
        end_run = paragraph.add_run()
        set_run_font(end_run, 9, color=DIM)
        end_run._r.append(end)

    field("PAGE")
    separator = paragraph.add_run("  /  ")
    set_run_font(separator, 9, color=DIM)
    field("NUMPAGES")


def paint_page(doc: Document) -> None:
    background = OxmlElement("w:background")
    background.set(qn("w:color"), CREAM_HEX)
    doc.element.insert(0, background)
    display = OxmlElement("w:displayBackgroundShape")
    doc.settings.element.append(display)


def band(paragraph, text: str, size: float, *, bold: bool = False, color: RGBColor = INK) -> None:
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1
    run = paragraph.add_run(text)
    set_run_font(run, size, bold=bold, color=color)


def configure(doc: Document, header_text: str) -> None:
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.4)
    section.bottom_margin = Cm(2.2)
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(1.0)

    normal = doc.styles["Normal"]
    normal.font.name = FONT_EN
    normal.font.size = Pt(11)
    normal.font.color.rgb = INK
    rpr = normal.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    fonts.set(qn("w:ascii"), FONT_EN)
    fonts.set(qn("w:hAnsi"), FONT_EN)
    fonts.set(qn("w:eastAsia"), FONT_CN)
    pf = normal.paragraph_format
    pf.line_spacing = 1.15
    pf.space_after = Pt(8)
    pf.space_before = Pt(0)
    paint_page(doc)

    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    band(hp, "普炳软件", 9, bold=True, color=ORANGE)
    tail = hp.add_run(f"    {header_text}")
    set_run_font(tail, 9, color=DIM)
    p_pr = hp._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "18")
    bottom.set(qn("w:space"), "6")
    bottom.set(qn("w:color"), ORANGE_HEX)
    p_bdr.append(bottom)
    p_pr.append(p_bdr)

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    band(fp, "普炳软件  ·  结构件自动核价平台", 9, color=DIM)
    fp.add_run("          ")
    add_page_number(fp)
    f_pr = fp._p.get_or_add_pPr()
    f_bdr = OxmlElement("w:pBdr")
    top = OxmlElement("w:top")
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), "6")
    top.set(qn("w:space"), "6")
    top.set(qn("w:color"), LINE_HEX)
    f_bdr.append(top)
    f_pr.append(f_bdr)


def paragraph_rule(paragraph, edge: str, size: str, space: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    border = OxmlElement("w:pBdr")
    line = OxmlElement(f"w:{edge}")
    line.set(qn("w:val"), "single")
    line.set(qn("w:sz"), size)
    line.set(qn("w:space"), space)
    line.set(qn("w:color"), ORANGE_HEX)
    border.append(line)
    p_pr.append(border)


def add_heading_text(doc: Document, text: str, level: int) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.line_spacing = 1.08
    if text == "结构件自动核价平台":
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(2)
        run = paragraph.add_run(text)
        set_run_font(run, 11, bold=True, color=ORANGE)
        return
    if level == 1:
        paragraph.paragraph_format.space_before = Pt(4)
        paragraph.paragraph_format.space_after = Pt(12)
        run = paragraph.add_run(text)
        set_run_font(run, 22, bold=True, color=INK)
        paragraph_rule(paragraph, "bottom", "12", "1")
        return
    paragraph.paragraph_format.space_before = Pt(16)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.left_indent = Cm(0.18)
    run = paragraph.add_run(text)
    set_run_font(run, 14, bold=True, color=INK)
    paragraph_rule(paragraph, "left", "16", "6")


def add_body(doc: Document, text: str, *, center: bool = False, size: float = 11) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.line_spacing = 1.15
    paragraph.paragraph_format.space_after = Pt(8)
    if center:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    color = MUTED if text.startswith("——") else INK
    add_marked_runs(paragraph, text, size, color=color)


def add_code(doc: Document, lines: list[str]) -> None:
    for line in lines:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.15
        paragraph.paragraph_format.left_indent = Cm(0.4)
        shade_paragraph(paragraph, SAND_HEX)
        run = paragraph.add_run(line if line else " ")
        set_run_font(run, 10, latin="Consolas", east=FONT_CN)


def is_signature_table(rows: list[list[str]]) -> bool:
    if len(rows) < 2 or len(rows[0]) != 2:
        return False
    left, right = rows[0][0], rows[0][1]
    return left.startswith("甲方：") and right.startswith("乙方：") and "联系人" not in left


def set_table_borders(table, *, visible: bool) -> None:
    tbl_pr = table._tbl.tblPr
    old = tbl_pr.find(qn("w:tblBorders"))
    if old is not None:
        tbl_pr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        if visible:
            element.set(qn("w:val"), "single")
            element.set(qn("w:sz"), "4")
            element.set(qn("w:color"), LINE_HEX)
        else:
            element.set(qn("w:val"), "nil")
            element.set(qn("w:sz"), "0")
            element.set(qn("w:color"), "auto")
        element.set(qn("w:space"), "0")
        borders.append(element)
    tbl_pr.append(borders)


def set_row_min_height(row, centimeters: float) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    height = OxmlElement("w:trHeight")
    height.set(qn("w:val"), str(int(centimeters * 567)))
    height.set(qn("w:hRule"), "atLeast")
    tr_pr.append(height)


def add_signature_table(doc: Document, rows: list[list[str]]) -> None:
    table = doc.add_table(rows=len(rows), cols=2)
    table.autofit = False
    set_table_borders(table, visible=False)
    widths = (Cm(8), Cm(8))
    for r_index, row in enumerate(rows):
        sign_row = any(cell.startswith(("代表签字", "授权代表")) for cell in row)
        if sign_row:
            set_row_min_height(table.rows[r_index], 2.4)
        for c_index, value in enumerate(row[:2]):
            cell = table.rows[r_index].cells[c_index]
            cell.width = widths[c_index]
            party = value.startswith(("甲方：", "乙方："))
            set_cell_text(cell, value, bold=party, frame="rule" if party else "none")
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(10 if party else 6)
            paragraph.paragraph_format.space_after = Pt(4)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)


def add_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    if is_signature_table(rows):
        add_signature_table(doc, rows)
        return
    width = len(rows[0])
    table = doc.add_table(rows=len(rows), cols=width)
    table.autofit = True
    set_table_borders(table, visible=True)
    for r_index, row in enumerate(rows):
        for c_index in range(width):
            value = row[c_index] if c_index < len(row) else ""
            set_cell_text(table.rows[r_index].cells[c_index], value, header=(r_index == 0))
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_rule(line: str) -> bool:
    return bool(re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", line.strip()))


def page_break(doc: Document) -> None:
    doc.add_page_break()


def write_markdown(doc: Document, lines: list[str], *, base: Path) -> None:
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        include = re.fullmatch(r"<!--\s*INCLUDE\s+(.+?)\s*-->", stripped)
        if include:
            included = (base / include.group(1)).read_text(encoding="utf-8").splitlines()
            write_markdown(doc, included, base=base)
            index += 1
            continue

        if stripped.startswith("```"):
            index += 1
            block: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index].rstrip())
                index += 1
            add_code(doc, block)
            index += 1
            continue

        if stripped.startswith("|"):
            raw_rows: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                raw_rows.append(lines[index].strip())
                index += 1
            parsed = [split_row(row) for row in raw_rows if not is_rule(row)]
            add_table(doc, parsed)
            continue

        if not stripped or stripped == "---":
            index += 1
            continue

        if "以下无正文" in stripped or stripped.startswith("# 附件"):
            page_break(doc)

        if stripped.startswith("# "):
            add_heading_text(doc, stripped[2:].strip(), 1)
            index += 1
            continue

        if stripped.startswith("## "):
            add_heading_text(doc, stripped[3:].strip(), 2)
            index += 1
            continue

        center = stripped.startswith("**（") or stripped.startswith("——")
        add_body(doc, stripped, center=center)
        index += 1


def render(path: Path, header: str) -> Document:
    doc = Document()
    configure(doc, header)
    write_markdown(doc, path.read_text(encoding="utf-8").splitlines(), base=path.parent)
    core = doc.core_properties
    core.author = "上海普炳软件科技有限公司"
    core.title = header
    return doc


def main() -> None:
    plan = render(HERE / "04-建设方案.md", "PB-COSTING-202611-001　建设方案")
    plan_path = HERE / "芜湖普威技研有限公司_结构件自动核价平台_建设方案.docx"
    plan.save(plan_path)

    contract = render(HERE / "05-产品与开发合同.md", "PB-COSTING-202611-001　产品与开发合同")
    contract_path = HERE / "芜湖普威技研有限公司_结构件自动核价平台_产品与开发合同.docx"
    contract.save(contract_path)

    print(plan_path)
    print(contract_path)


if __name__ == "__main__":
    main()
