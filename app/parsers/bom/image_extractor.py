"""
BOM Excel 简图抽取

材料清单中大量图片为 WMF，openpyxl 会丢弃；因此直接从 xlsx ZIP
读取 xl/drawings + xl/media，再转为 PNG。

列约定（0-based）：
- 4 = 总成图示（E 列）→ 归属 L0 供货总成
- 15 = 单件图示（P 列）→ 有 L2 归 L2；无 L2 时归 L1（一级零件图）
图常浮在名称格上，锚点可落在左邻列（D / O），按同族简图收录。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from PIL import Image

logger = logging.getLogger("parser.bom.image")

_NS = {
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
_R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"

# 只抽取业务图示列（含左邻：图常锚在名称列）
ASSEMBLY_SKETCH_COL = 4  # E
PART_SKETCH_COL = 15  # P


def sketch_col_family(col_0idx: int) -> int | None:
    """锚点列归到表头简图列：E 或其左邻 D → 总成；P 或其左邻 O → 单件。"""
    if col_0idx in {ASSEMBLY_SKETCH_COL, ASSEMBLY_SKETCH_COL - 1}:
        return ASSEMBLY_SKETCH_COL
    if col_0idx in {PART_SKETCH_COL, PART_SKETCH_COL - 1}:
        return PART_SKETCH_COL
    return None


@dataclass
class BomImageAnchor:
    """一张图示的锚点与 PNG 字节"""

    excel_row: int  # 1-based
    col_0idx: int
    png_bytes: bytes
    source_name: str | None = None


def extract_bom_images(source: str | Path | bytes) -> list[BomImageAnchor]:
    """从 xlsx 抽取总成/单件图示，统一转为 PNG。"""
    if isinstance(source, bytes | bytearray):
        zip_file = ZipFile(BytesIO(source))
    else:
        zip_file = ZipFile(str(source))

    try:
        drawing_paths = [
            name
            for name in zip_file.namelist()
            if name.startswith("xl/drawings/drawing") and name.endswith(".xml")
        ]
        if not drawing_paths:
            logger.info("BOM 简图: 未找到 drawing XML")
            return []

        results: list[BomImageAnchor] = []
        for drawing_path in sorted(drawing_paths):
            rels_path = drawing_path.replace("xl/drawings/", "xl/drawings/_rels/") + ".rels"
            rid_map = _load_rid_map(zip_file, rels_path)
            try:
                drawing_xml = zip_file.read(drawing_path)
            except KeyError:
                continue
            results.extend(_parse_drawing(zip_file, drawing_xml, rid_map))

        logger.info(
            "BOM 简图抽取: %s 张 (总成列=%s, 单件列=%s)",
            len(results),
            sum(1 for x in results if sketch_col_family(x.col_0idx) == ASSEMBLY_SKETCH_COL),
            sum(1 for x in results if sketch_col_family(x.col_0idx) == PART_SKETCH_COL),
        )
        return results
    finally:
        zip_file.close()


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
        # Target 形如 ../media/image1.wmf
        normalized = target.replace("\\", "/")
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
) -> list[BomImageAnchor]:
    root = ET.fromstring(drawing_xml)
    out: list[BomImageAnchor] = []
    skipped = 0

    for anchor in list(root):
        frm = anchor.find("xdr:from", _NS)
        if frm is None:
            skipped += 1
            continue
        try:
            col = int(frm.findtext("xdr:col", default="-1", namespaces=_NS))
            row_0 = int(frm.findtext("xdr:row", default="-1", namespaces=_NS))
        except (TypeError, ValueError):
            skipped += 1
            continue
        if sketch_col_family(col) is None or row_0 < 0:
            skipped += 1
            continue

        blip = anchor.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
        if blip is None:
            skipped += 1
            continue
        rid = blip.attrib.get(_R_EMBED)
        media_path = rid_map.get(rid or "")
        if not media_path:
            skipped += 1
            continue

        try:
            raw = zip_file.read(media_path)
        except KeyError:
            skipped += 1
            continue

        png_bytes = _to_png_bytes(raw, media_path)
        if not png_bytes:
            skipped += 1
            continue

        out.append(
            BomImageAnchor(
                excel_row=row_0 + 1,
                col_0idx=col,
                png_bytes=png_bytes,
                source_name=Path(media_path).name,
            )
        )

    if skipped:
        logger.debug("BOM drawing 跳过锚点: %s", skipped)
    return out


def _to_png_bytes(raw: bytes, media_path: str) -> bytes | None:
    """任意嵌入图转为 PNG；WMF 在 Windows + Pillow 下可打开。"""
    if not raw:
        return None
    suffix = Path(media_path).suffix.lower()
    # 已是 PNG
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return raw
    try:
        image: Image.Image = Image.open(BytesIO(raw))
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        elif image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as exc:
        logger.warning("简图转 PNG 失败 %s (%s): %s", media_path, suffix, exc)
        return None
