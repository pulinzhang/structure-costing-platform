"""八种填法总览，一张卡通。源文件随设计文档永久保留。

一物一码：图变更即为另一物料，另一物料必须另给一码。
完成停止没有新图，不另给码。其余七种先把总成换成新号，再看这一层。
运行：python -X utf8 docs/engineering-change/design-change/draw_eight_overview.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).with_name("八种填法.png")

W, H = 2200, 1480
SCALE = 2
INK = (58, 46, 36)
MUTED = (122, 106, 92)
PAPER = (255, 247, 241, 255)
WHITE = (255, 253, 250, 255)
GREEN = (31, 138, 76)
GREEN_SOFT = (226, 244, 232, 255)
ROSE = (184, 72, 96)
ROSE_SOFT = (255, 236, 240, 255)
ORANGE = (204, 106, 32)
ORANGE_SOFT = (255, 241, 228, 255)
BLUE = (52, 108, 186)
BLUE_SOFT = (230, 239, 250, 255)
GRAY = (132, 122, 114)
GRAY_SOFT = (244, 240, 236, 255)
BLUSH = (255, 186, 176, 220)

FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


def px(value: float) -> int:
    return int(round(value * SCALE))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_PATH, px(size))


def text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    content: str,
    face: ImageFont.FreeTypeFont,
    fill: tuple[int, ...],
    anchor: str = "mm",
) -> None:
    draw.text((px(xy[0]), px(xy[1])), content, font=face, fill=fill, anchor=anchor)


def shadow(base: Image.Image, box: tuple[float, float, float, float], radius: int) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(
        (px(x0 + 6), px(y0 + 14), px(x1 + 6), px(y1 + 18)),
        px(radius),
        fill=(120, 80, 50, 28),
    )
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(px(16))))


def face(draw: ImageDraw.ImageDraw, cx: float, cy: float, mood: str, scale: float) -> None:
    width = max(px(2), px(3.2 * scale))
    if mood == "sleep":
        for sign in (-1, 1):
            eye_x = cx + sign * 16 * scale
            draw.arc(
                (
                    px(eye_x - 11 * scale),
                    px(cy - 7 * scale),
                    px(eye_x + 11 * scale),
                    px(cy + 8 * scale),
                ),
                200,
                340,
                fill=INK,
                width=width,
            )
        draw.arc(
            (px(cx - 8 * scale), px(cy + 10 * scale), px(cx + 8 * scale), px(cy + 20 * scale)),
            20,
            160,
            fill=INK,
            width=width,
        )
        return
    eye_w, eye_h, gap = 6.2 * scale, 8.2 * scale, 13 * scale
    for sign in (-1, 1):
        ex = cx + sign * gap
        draw.ellipse((px(ex - eye_w), px(cy - eye_h), px(ex + eye_w), px(cy + eye_h)), fill=INK)
        draw.ellipse(
            (
                px(ex - eye_w * 0.55),
                px(cy - eye_h * 0.72),
                px(ex - eye_w * 0.05),
                px(cy - eye_h * 0.15),
            ),
            fill=WHITE,
        )
    if mood == "plain":
        draw.line(
            (px(cx - 9 * scale), px(cy + 16 * scale), px(cx + 9 * scale), px(cy + 16 * scale)),
            fill=INK,
            width=width,
        )
        return
    if scale >= 1.2:
        draw.ellipse(
            (px(cx - 32 * scale), px(cy + 8 * scale), px(cx - 16 * scale), px(cy + 18 * scale)),
            fill=BLUSH,
        )
        draw.ellipse(
            (px(cx + 16 * scale), px(cy + 8 * scale), px(cx + 32 * scale), px(cy + 18 * scale)),
            fill=BLUSH,
        )
    draw.arc(
        (px(cx - 12 * scale), px(cy + 8 * scale), px(cx + 12 * scale), px(cy + 24 * scale)),
        18,
        162,
        fill=INK,
        width=width,
    )


def hero(
    base: Image.Image,
    cx: float,
    cy: float,
    name: str,
    caption: str,
    mood: str,
    accent: tuple[int, int, int],
    soft: tuple[int, int, int, int],
) -> None:
    body = (cx - 102, cy - 108, cx + 102, cy + 96)
    shadow(base, body, 72)
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle(
        (px(body[0]), px(body[1]), px(body[2]), px(body[3])),
        px(72),
        fill=soft,
        outline=accent,
        width=px(5),
    )
    face(draw, cx, cy - 22, mood, 1.45)
    text(draw, (cx, cy + 52), name, font(40, True), accent)
    text(draw, (cx, cy + 148), caption, font(22), MUTED)


def fitted(content: str, max_width: float, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    face = font(size, bold)
    while size > 14 and face.getlength(content) > px(max_width):
        size -= 1
        face = font(size, bold)
    return face


def badge(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    label: str,
    accent: tuple[int, int, int],
    soft: tuple[int, int, int, int],
    mood: str | None,
    wide: float = 132,
    tall: float = 112,
) -> tuple[float, float, float, float]:
    box = (cx - wide / 2, cy - tall / 2, cx + wide / 2, cy + tall / 2)
    draw.rounded_rectangle(
        (px(box[0]), px(box[1]), px(box[2]), px(box[3])),
        px(36),
        fill=soft,
        outline=accent,
        width=px(4),
    )
    if mood is None:
        text(draw, (cx, cy), label, fitted(label, wide - 28, 22), accent)
        return box
    face(draw, cx, cy - 16, mood, 0.7)
    text(draw, (cx, cy + 32), label, fitted(label, wide - 24, 18), accent)
    return box


def plus_badge(
    draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], accent: tuple[int, int, int]
) -> None:
    cx, cy, radius = box[2] - 8, box[1] + 8, 15
    draw.ellipse(
        (px(cx - radius), px(cy - radius), px(cx + radius), px(cy + radius)),
        fill=accent,
        outline=WHITE,
        width=px(3),
    )
    draw.line((px(cx - 7), px(cy), px(cx + 7), px(cy)), fill=WHITE, width=px(3))
    draw.line((px(cx), px(cy - 7), px(cx), px(cy + 7)), fill=WHITE, width=px(3))


def arrow(
    draw: ImageDraw.ImageDraw, x0: float, x1: float, y: float, color: tuple[int, int, int]
) -> None:
    draw.line((px(x0), px(y), px(x1 - 16), px(y)), fill=color, width=px(6))
    draw.polygon(
        [(px(x1), px(y)), (px(x1 - 18), px(y - 11)), (px(x1 - 18), px(y + 11))],
        fill=color,
    )


def tree(
    draw: ImageDraw.ImageDraw,
    parent: tuple[float, float, float, float],
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> None:
    px_mid = (parent[0] + parent[2]) / 2
    parent_bottom = parent[3]
    left_x = (left[0] + left[2]) / 2
    right_x = (right[0] + right[2]) / 2
    child_top = left[1]
    bar = (parent_bottom + child_top) / 2
    width = px(4)
    draw.line((px(px_mid), px(parent_bottom), px(px_mid), px(bar)), fill=INK, width=width)
    draw.line((px(left_x), px(bar), px(right_x), px(bar)), fill=INK, width=width)
    draw.line((px(left_x), px(bar), px(left_x), px(child_top)), fill=INK, width=width)
    draw.line((px(right_x), px(bar), px(right_x), px(child_top)), fill=INK, width=width)
    joint = px(2.4)
    for x, y in (
        (px_mid, parent_bottom),
        (px_mid, bar),
        (left_x, bar),
        (right_x, bar),
        (left_x, child_top),
        (right_x, child_top),
    ):
        draw.ellipse((px(x) - joint, px(y) - joint, px(x) + joint, px(y) + joint), fill=INK)


def zero_mark(draw: ImageDraw.ImageDraw, cx: float, cy: float) -> None:
    radius = 20
    draw.ellipse(
        (px(cx - radius), px(cy - radius), px(cx + radius), px(cy + radius)),
        fill=ROSE_SOFT,
        outline=ROSE,
        width=px(3),
    )
    text(draw, (cx, cy), "0", font(20, True), ROSE)


@dataclass(frozen=True, slots=True)
class Tile:
    index: str
    title: str
    foot: str
    accent: tuple[int, int, int]
    kind: str
    unmarked: bool = False


TILES = (
    Tile("01", "完成停止", "整个总成不再交", GRAY, "stop"),
    Tile("02", "此件不装", "号不动，用量写 0", ROSE, "skip1"),
    Tile("03", "增加零件", "新号不要写成总成号", ORANGE, "add1"),
    Tile("04", "改图", "旧号写成新号", GREEN, "rev1"),
    Tile("05", "增加分总成", "下面有几颗写几颗", ORANGE, "leaf"),
    Tile("06", "此件不装", "一级换新号，这颗不装", ROSE, "skip2", True),
    Tile("07", "增加零件", "原来要已有二级才收", ORANGE, "add2", True),
    Tile("08", "改图", "分总成和这颗一起换号", GREEN, "rev2"),
)


def draw_scene(draw: ImageDraw.ImageDraw, kind: str, cx: float, cy: float) -> None:
    if kind == "stop":
        badge(draw, cx - 118, cy, "AA", GRAY, GRAY_SOFT, "sleep", 124, 108)
        arrow(draw, cx - 48, cx + 36, cy, GRAY)
        badge(draw, cx + 112, cy, "空着", GRAY, GRAY_SOFT, None, 112, 108)
        return
    if kind == "skip1":
        badge(draw, cx - 118, cy, "原号", ROSE, ROSE_SOFT, "sleep", 124, 108)
        zero_mark(draw, cx, cy)
        badge(draw, cx + 118, cy, "空着", GRAY, GRAY_SOFT, None, 112, 108)
        return
    if kind == "rev1":
        badge(draw, cx - 122, cy, "旧号", BLUE, BLUE_SOFT, "plain", 124, 108)
        arrow(draw, cx - 52, cx + 40, cy, GREEN)
        badge(draw, cx + 118, cy, "新号", GREEN, GREEN_SOFT, "smile", 124, 108)
        return
    if kind == "add1":
        parent = badge(draw, cx, cy - 92, "总成", GREEN, GREEN_SOFT, None, 120, 72)
        child = badge(draw, cx, cy + 78, "新号", ORANGE, ORANGE_SOFT, "smile", 124, 108)
        tree(draw, parent, child, child)
        plus_badge(draw, child, ORANGE)
        return

    parent_label = {
        "skip2": "一级新号",
        "add2": "一级新号",
        "rev2": "分总成新号",
        "leaf": "新分总成",
    }[kind]
    left_label = {"skip2": "不装", "add2": "新号", "rev2": "新号", "leaf": "原号"}[kind]
    right_label = {"skip2": "原号", "add2": "原号", "rev2": "原号", "leaf": "新号"}[kind]
    parent_accent = ORANGE if kind == "leaf" else GREEN
    parent_soft = ORANGE_SOFT if kind == "leaf" else GREEN_SOFT
    if kind == "skip2":
        left_accent, left_soft, left_mood = ROSE, ROSE_SOFT, "sleep"
    elif kind == "leaf":
        left_accent, left_soft, left_mood = GRAY, GRAY_SOFT, None
    elif kind == "add2":
        left_accent, left_soft, left_mood = ORANGE, ORANGE_SOFT, "smile"
    else:
        left_accent, left_soft, left_mood = GREEN, GREEN_SOFT, "smile"
    if kind == "leaf":
        right_accent, right_soft, right_mood = ORANGE, ORANGE_SOFT, "smile"
    else:
        right_accent, right_soft, right_mood = GRAY, GRAY_SOFT, None
    parent = badge(draw, cx, cy - 96, parent_label, parent_accent, parent_soft, "smile", 176, 108)
    left = badge(draw, cx - 108, cy + 82, left_label, left_accent, left_soft, left_mood, 124, 104)
    right = badge(
        draw, cx + 108, cy + 82, right_label, right_accent, right_soft, right_mood, 124, 104
    )
    tree(draw, parent, left, right)
    if kind == "add2":
        plus_badge(draw, left, ORANGE)


def draw_tile(base: Image.Image, tile: Tile, box: tuple[float, float, float, float]) -> None:
    shadow(base, box, 28)
    draw = ImageDraw.Draw(base)
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((px(x0), px(y0), px(x1), px(y1)), px(28), fill=WHITE)
    text(draw, (x0 + 28, y0 + 40), tile.index, font(18, True), tile.accent, "lm")
    text(draw, (x0 + 72, y0 + 40), tile.title, font(24, True), INK, "lm")
    if tile.unmarked:
        mark = "模板没画"
        mark_font = font(14, True)
        width = mark_font.getlength(mark) / SCALE + 22
        draw.rounded_rectangle(
            (px(x1 - width - 18), px(y0 + 22), px(x1 - 18), px(y0 + 52)),
            px(14),
            fill=(255, 236, 240, 255),
        )
        text(draw, (x1 - 18 - width / 2, y0 + 37), mark, mark_font, ROSE)
    draw_scene(draw, tile.kind, (x0 + x1) / 2, (y0 + 86 + y1 - 52) / 2)
    text(draw, ((x0 + x1) / 2, y1 - 28), tile.foot, font(17), MUTED)


def band(draw: ImageDraw.ImageDraw, x: float, y: float, title: str, note: str) -> None:
    title_font = font(26, True)
    text(draw, (x, y), title, title_font, INK, "lm")
    text(draw, (x + title_font.getlength(title) / SCALE + 14, y + 1), note, font(18), MUTED, "lm")


def main() -> None:
    image = Image.new("RGBA", (px(W), px(H)), PAPER)
    draw = ImageDraw.Draw(image)
    draw.ellipse((px(-260), px(-220), px(560), px(460)), fill=(255, 228, 214, 255))
    draw.ellipse((px(1680), px(H - 420), px(2460), px(H + 220)), fill=(226, 244, 232, 255))

    text(draw, (W / 2, 48), "八种填法", font(52, True), INK)
    text(
        draw,
        (W / 2, 108),
        "先看层级，再对上变更单里的那句话。完成停止不换总成号，其余都要另给。",
        font(22),
        INK,
    )

    gap = 20
    margin = 48
    card_w = (W - margin * 2 - gap * 3) / 4
    stop_h = 280
    card_h = 430
    stop_top = 168
    level1_top = stop_top + stop_h + 52
    level2_top = level1_top + card_h + 52

    band(draw, margin, stop_top - 26, "总成", "不换号")
    draw_tile(image, TILES[0], (margin, stop_top, margin + card_w, stop_top + stop_h))

    band(draw, margin, level1_top - 26, "一级", "总成号另给，只填这一层")
    for column, tile in enumerate(TILES[1:5]):
        x0 = margin + column * (card_w + gap)
        draw_tile(image, tile, (x0, level1_top, x0 + card_w, level1_top + card_h))

    band(draw, margin, level2_top - 26, "二级", "和上面同一列是同一件事")
    for column, tile in enumerate(TILES[5:]):
        x0 = margin + column * (card_w + gap)
        draw_tile(image, tile, (x0, level2_top, x0 + card_w, level2_top + card_h))

    image.resize((W, H), Image.Resampling.LANCZOS).convert("RGB").save(OUT, "PNG", optimize=True)
    print(OUT)


if __name__ == "__main__":
    main()
