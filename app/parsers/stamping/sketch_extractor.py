"""冲压工艺简图：从 xlsx ZIP 读 drawing，含 openpyxl 会丢掉的 WMF。"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from app.common.sketch_png import media_bytes_to_png
from app.utils.logging_config import get_logger

logger = get_logger("parser.stamping.sketch")

_NS = {
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}
_R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
_R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


@dataclass(frozen=True, slots=True)
class SketchAnchor:
    """一张零件简图的锚点与 PNG 字节。"""

    excel_row: int
    col_0idx: int
    png_bytes: bytes


def extract_stamping_sketches(
    file_path: str,
    allowed_cols_0idx: frozenset[int],
    *,
    sheet_name: str | None = None,
) -> list[SketchAnchor]:
    """抽取简图列（及左邻列）上的嵌入图，统一成 PNG。工程变更可限定工作表，避免材料清单的图抢行。"""
    if not file_path.lower().endswith(".xlsx") or not allowed_cols_0idx:
        return []
    try:
        zip_file = ZipFile(file_path)
    except (OSError, BadZipFile):
        return []

    try:
        drawing_paths = [
            name
            for name in zip_file.namelist()
            if name.startswith("xl/drawings/drawing") and name.endswith(".xml")
        ]
        if sheet_name:
            allowed = _drawing_paths_for_sheet(zip_file, sheet_name)
            drawing_paths = [path for path in drawing_paths if path in allowed]
        results: list[SketchAnchor] = []
        for drawing_path in sorted(drawing_paths):
            rels_path = drawing_path.replace("xl/drawings/", "xl/drawings/_rels/") + ".rels"
            rid_map = _load_rid_map(zip_file, rels_path)
            try:
                drawing_xml = zip_file.read(drawing_path)
            except KeyError:
                continue
            results.extend(_parse_drawing(zip_file, drawing_xml, rid_map, allowed_cols_0idx))
        logger.info("冲压简图抽取: %s 张, 列=%s", len(results), sorted(allowed_cols_0idx))
        return results
    finally:
        zip_file.close()


def _drawing_paths_for_sheet(zip_file: ZipFile, sheet_name: str) -> set[str]:
    try:
        workbook_xml = zip_file.read("xl/workbook.xml")
        rels_xml = zip_file.read("xl/_rels/workbook.xml.rels")
    except KeyError:
        return set()
    rid_to_target: dict[str, str] = {}
    for rel in ET.fromstring(rels_xml):
        rid = rel.attrib.get("Id")
        target = (rel.attrib.get("Target") or "").replace("\\", "/")
        if rid and target:
            rid_to_target[rid] = target
    workbook_root = ET.fromstring(workbook_xml)
    sheet_target = None
    for sheet in workbook_root.findall("main:sheets/main:sheet", _NS):
        if sheet.attrib.get("name") != sheet_name:
            continue
        rid = sheet.attrib.get(_R_ID)
        sheet_target = rid_to_target.get(rid or "")
        break
    if not sheet_target:
        return set()
    sheet_target = sheet_target.lstrip("/")
    sheet_path = sheet_target if sheet_target.startswith("xl/") else "xl/" + sheet_target
    rels_path = sheet_path.replace("xl/worksheets/", "xl/worksheets/_rels/") + ".rels"
    try:
        sheet_rels = zip_file.read(rels_path)
    except KeyError:
        return set()
    found: set[str] = set()
    for rel in ET.fromstring(sheet_rels):
        rel_type = rel.attrib.get("Type") or ""
        target = (rel.attrib.get("Target") or "").replace("\\", "/").lstrip("/")
        if "drawing" not in rel_type.lower() or not target:
            continue
        if target.startswith("../"):
            found.add("xl/" + target[3:])
        elif target.startswith("xl/"):
            found.add(target)
        else:
            found.add("xl/drawings/" + target)
    return found


def _load_rid_map(zip_file: ZipFile, rels_path: str) -> dict[str, str]:
    try:
        rels_xml = zip_file.read(rels_path)
    except KeyError:
        return {}
    root = ET.fromstring(rels_xml)
    mapping: dict[str, str] = {}
    for rel in root:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if not rid or not target:
            continue
        normalized = target.replace("\\", "/").lstrip("/")
        if normalized.startswith("../"):
            normalized = "xl/" + normalized[3:]
        elif not normalized.startswith("xl/"):
            normalized = "xl/drawings/" + normalized
        mapping[rid] = normalized
    return mapping


def _parse_drawing(
    zip_file: ZipFile,
    drawing_xml: bytes,
    rid_map: dict[str, str],
    allowed_cols_0idx: frozenset[int],
) -> list[SketchAnchor]:
    root = ET.fromstring(drawing_xml)
    out: list[SketchAnchor] = []
    for anchor in list(root):
        frm = anchor.find("xdr:from", _NS)
        if frm is None:
            continue
        try:
            col = int(frm.findtext("xdr:col", default="-1", namespaces=_NS))
            row_0 = int(frm.findtext("xdr:row", default="-1", namespaces=_NS))
        except (TypeError, ValueError):
            continue
        if col not in allowed_cols_0idx or row_0 < 0:
            continue
        blip = anchor.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
        if blip is None:
            continue
        media_path = rid_map.get(blip.attrib.get(_R_EMBED) or "")
        if not media_path:
            continue
        try:
            raw = zip_file.read(media_path)
        except KeyError:
            continue
        png_bytes = media_bytes_to_png(raw, media_path)
        if not png_bytes:
            continue
        out.append(SketchAnchor(excel_row=row_0 + 1, col_0idx=col, png_bytes=png_bytes))
    return out
