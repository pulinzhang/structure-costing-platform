"""设计变更场景图的源文件，随设计文档永久保留。

由易到难，一张一个场景。完成停止不换总成号。
其余每张都是因为此件不装、增加零件或零件改图，总成图变了，所以要先换总成号。
下载模板没画的（此件不装二级、增加零件二级）规则仍收，图上单独标出。
运行：python -X utf8 docs/engineering-change/design-change/draw_five_scenarios.py
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = Path(__file__).with_name("scenes")
OLD_POSTER = Path(__file__).with_name("五种改法-零件号住在材料清单.png")

W, H = 1920, 1180
INK = (58, 46, 36)
MUTED = (122, 106, 92)
PAPER = (255, 246, 238, 255)
WHITE = (255, 253, 250, 255)
GREEN = (31, 138, 76)
GREEN_SOFT = (229, 246, 236, 255)
BLUE = (47, 111, 237)
BLUE_SOFT = (231, 240, 255, 255)
ORANGE = (224, 122, 31)
ORANGE_SOFT = (255, 241, 227, 255)
RED = (209, 67, 67)
RED_SOFT = (253, 236, 236, 255)
AMBER = (184, 110, 18)
AMBER_SOFT = (255, 244, 224, 255)
GRAY = (120, 110, 102)
GRAY_SOFT = (243, 240, 236, 255)
ROSE = (196, 92, 122)
ROSE_SOFT = (255, 236, 242, 255)
PURPLE = (91, 75, 138)
PURPLE_SOFT = (240, 236, 248, 255)

FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_PATH, size)


def text(
    draw: ImageDraw.ImageDraw, xy: tuple[float, float], content: str, face, fill, anchor: str = "mm"
) -> None:
    draw.text(xy, content, font=face, fill=fill, anchor=anchor)


def shadow(base: Image.Image, box: tuple[int, int, int, int], radius: int = 28) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0 + 4, y0 + 8, x1 + 4, y1 + 10), radius, fill=(90, 60, 30, 28))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(10)))


def token(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    caption: str,
    value: str,
    accent: tuple[int, int, int],
    soft: tuple[int, int, int, int],
) -> None:
    draw.rounded_rectangle(box, 22, fill=soft, outline=accent, width=5)
    cx = (box[0] + box[2]) / 2
    height = box[3] - box[1]
    width = box[2] - box[0]
    value_size = 52 if height >= 180 else 34
    face = font(value_size, True)
    while value_size > 22 and face.getlength(value) > width - 40:
        value_size -= 2
        face = font(value_size, True)
    text(draw, (cx, box[1] + height * 0.32), caption, font(22), MUTED)
    text(draw, (cx, box[1] + height * 0.68), value, face, accent)


def arrow(
    draw: ImageDraw.ImageDraw, x0: float, x1: float, y: float, color: tuple[int, int, int]
) -> None:
    direction = 1 if x1 > x0 else -1
    head = 16
    draw.line((x0, y, x1 - direction * head, y), fill=color, width=8)
    draw.polygon(
        [(x1, y), (x1 - direction * head, y - 11), (x1 - direction * head, y + 11)], fill=color
    )


def vline(
    draw: ImageDraw.ImageDraw, x: float, y0: float, y1: float, color: tuple[int, int, int]
) -> None:
    draw.line((x, y0, x, y1), fill=color, width=6)


@dataclass(frozen=True, slots=True)
class Scene:
    filename: str
    title: str
    change_type: str
    level: str
    color: tuple[int, int, int]
    soft: tuple[int, int, int, int]
    changes_assembly: bool
    step2_title: str
    step2_line: str
    kind: str
    template_label: str
    next_title: str


SCENES = (
    Scene(
        "01-完成停止.png",
        "完成停止",
        "完成停止",
        "总成",
        GRAY,
        GRAY_SOFT,
        False,
        "材料清单不写这个总成",
        "整个总成不再交。",
        "stop",
        "模板里有",
        "此件不装 · 一级",
    ),
    Scene(
        "02-此件不装-一级.png",
        "此件不装 · 一级",
        "此件不装",
        "一级",
        ROSE,
        ROSE_SOFT,
        True,
        "这颗零件号不动",
        "用量写 0，备注写「此件不装」。",
        "not_install",
        "模板里有",
        "此件不装 · 二级",
    ),
    Scene(
        "03-此件不装-二级.png",
        "此件不装 · 二级",
        "此件不装",
        "二级",
        ROSE,
        ROSE_SOFT,
        True,
        "二级这颗号不动",
        "这颗用量写 0。旁边的二级还是原号。",
        "not_install_l2",
        "模板没画，规则收",
        "增加一级",
    ),
    Scene(
        "04-增加一级.png",
        "增加一级",
        "增加零件",
        "一级",
        ORANGE,
        ORANGE_SOFT,
        True,
        "在总成下面加一颗",
        "新零件号不要写成总成号。",
        "add_l1",
        "模板里有",
        "增加二级",
    ),
    Scene(
        "05-增加二级.png",
        "增加二级",
        "增加零件",
        "二级",
        AMBER,
        AMBER_SOFT,
        True,
        "在一级件下面加一颗",
        "一级换成新号。旁边的二级还是原号。",
        "add_l2",
        "模板没画，规则收",
        "末级改图 · 一级",
    ),
    Scene(
        "06-末级改图-一级.png",
        "末级改图 · 一级",
        "改图",
        "一级",
        GREEN,
        GREEN_SOFT,
        True,
        "这颗末级换成新号",
        "变更前零件写旧号，变更后零件写新号。",
        "revise_l1",
        "模板里有",
        "末级改图 · 二级",
    ),
    Scene(
        "07-末级改图-二级.png",
        "末级改图 · 二级",
        "改图",
        "二级",
        PURPLE,
        PURPLE_SOFT,
        True,
        "从总成写到这颗末级",
        "分总成换成新号。旁边的二级还是原号。",
        "revise_l2",
        "模板里有",
        "",
    ),
)


def draw_header(draw: ImageDraw.ImageDraw, scene: Scene, index: int) -> None:
    text(draw, (56, 58), f"{index} / {len(SCENES)}", font(28, True), MUTED, "lm")
    text(draw, (150, 54), scene.title, font(42, True), scene.color, "lm")
    pills = (f"变更类型：{scene.change_type}", f"零件层级：{scene.level}", scene.template_label)
    x = 1880
    for label in reversed(pills):
        face = font(22, True)
        width = int(face.getlength(label)) + 36
        x -= width
        draw.rounded_rectangle((x, 28, x + width, 84), 18, fill=scene.soft)
        text(draw, (x + width / 2, 56), label, face, scene.color)
        x -= 16


def draw_step1(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    card = (40, 120, 1880, 500)
    accent = GREEN if scene.changes_assembly else GRAY
    title = "先换总成号" if scene.changes_assembly else "总成号不换"
    draw.rounded_rectangle(card, 28, fill=WHITE, outline=accent, width=4)
    draw.ellipse((48, 136, 96, 184), fill=accent)
    text(draw, (72, 160), "1", font(28, True), WHITE)
    text(draw, (116, 160), title, font(32, True), accent, "lm")
    left = (470, 230, 850, 450)
    right = (1070, 230, 1450, 450)
    token(draw, left, "变更前总成", "AA", BLUE, BLUE_SOFT)
    arrow(draw, 870, 1050, 340, accent)
    if scene.changes_assembly:
        token(draw, right, "变更后总成", "AB", GREEN, GREEN_SOFT)
        text(draw, (960, 478), "总成图变了，是因为下面这件事。", font(22), MUTED)
    else:
        token(draw, right, "变更后总成", "空着", GRAY, GRAY_SOFT)


def draw_step2_frame(draw: ImageDraw.ImageDraw, scene: Scene) -> tuple[int, int, int, int]:
    card = (40, 524, 1880, 1088)
    draw.rounded_rectangle(card, 28, fill=WHITE, outline=scene.color, width=4)
    draw.ellipse((48, 548, 96, 596), fill=scene.color)
    text(draw, (72, 572), "2", font(28, True), WHITE)
    text(draw, (116, 572), scene.step2_title, font(32, True), scene.color, "lm")
    text(draw, (960, 1048), scene.step2_line, font(26), INK)
    return (80, 630, 1840, 1000)


def draw_not_install(draw: ImageDraw.ImageDraw, area: tuple[int, int, int, int]) -> None:
    token(draw, (520, 700, 900, 960), "这颗零件", "原号", ROSE, ROSE_SOFT)
    token(draw, (1020, 700, 1400, 960), "变更后零件", "空着", GRAY, GRAY_SOFT)


def cross_out(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    inset = 22
    color = (209, 67, 67, 230)
    draw.line((x0 + inset, y0 + inset, x1 - inset, y1 - inset), fill=color, width=14)
    draw.line((x1 - inset, y0 + inset, x0 + inset, y1 - inset), fill=color, width=14)


def draw_not_install_l2(draw: ImageDraw.ImageDraw, area: tuple[int, int, int, int]) -> None:
    token(draw, (760, 632, 1160, 728), "总成", "AB", GREEN, GREEN_SOFT)
    vline(draw, 960, 728, 744, ROSE)
    token(draw, (760, 744, 1160, 840), "一级", "一级新号", ROSE, ROSE_SOFT)
    draw.line([(960, 840), (960, 868), (660, 868), (660, 888)], fill=ROSE, width=6)
    draw.line([(960, 868), (1260, 868), (1260, 888)], fill=GRAY, width=6)
    skipped = (460, 888, 860, 998)
    token(draw, skipped, "这颗二级", "原号", ROSE, ROSE_SOFT)
    cross_out(draw, skipped)
    token(draw, (1060, 888, 1460, 998), "别的二级", "原号", GRAY, GRAY_SOFT)


def draw_add_l1(draw: ImageDraw.ImageDraw, area: tuple[int, int, int, int]) -> None:
    token(draw, (760, 660, 1160, 830), "总成", "AB", GREEN, GREEN_SOFT)
    vline(draw, 960, 830, 870, ORANGE)
    token(draw, (760, 870, 1160, 990), "一级 · 新零件", "新号", ORANGE, ORANGE_SOFT)


def draw_add_l2(draw: ImageDraw.ImageDraw, area: tuple[int, int, int, int]) -> None:
    token(draw, (760, 632, 1160, 728), "总成", "AB", GREEN, GREEN_SOFT)
    vline(draw, 960, 728, 744, AMBER)
    token(draw, (760, 744, 1160, 840), "一级", "一级新号", AMBER, AMBER_SOFT)
    draw.line([(960, 840), (960, 868), (660, 868), (660, 888)], fill=AMBER, width=6)
    draw.line([(960, 868), (1260, 868), (1260, 888)], fill=GRAY, width=6)
    token(draw, (460, 888, 860, 998), "新加的二级", "这颗新号 +", AMBER, AMBER_SOFT)
    token(draw, (1060, 888, 1460, 998), "原来的二级", "原号", GRAY, GRAY_SOFT)


def draw_revise_l1(draw: ImageDraw.ImageDraw, area: tuple[int, int, int, int]) -> None:
    token(draw, (430, 720, 810, 960), "变更前零件 · 末级", "旧号", BLUE, BLUE_SOFT)
    arrow(draw, 840, 1080, 840, GREEN)
    token(draw, (1110, 720, 1490, 960), "变更后零件 · 末级", "新号", GREEN, GREEN_SOFT)


def draw_revise_l2(draw: ImageDraw.ImageDraw, area: tuple[int, int, int, int]) -> None:
    token(draw, (760, 632, 1160, 728), "总成", "AB", GREEN, GREEN_SOFT)
    vline(draw, 960, 728, 744, PURPLE)
    token(draw, (760, 744, 1160, 840), "分总成", "上级新号", PURPLE, PURPLE_SOFT)
    draw.line([(960, 840), (960, 868), (660, 868), (660, 888)], fill=PURPLE, width=6)
    draw.line([(960, 868), (1260, 868), (1260, 888)], fill=GRAY, width=6)
    token(draw, (460, 888, 860, 998), "这颗末级", "这颗新号", PURPLE, PURPLE_SOFT)
    token(draw, (1060, 888, 1460, 998), "其它二级", "原号", GRAY, GRAY_SOFT)


def draw_stop_detail(draw: ImageDraw.ImageDraw, area: tuple[int, int, int, int]) -> None:
    token(draw, (660, 700, 1260, 960), "材料清单", "不写这个总成", GRAY, GRAY_SOFT)


def draw_scene(scene: Scene, index: int) -> Path:
    image = Image.new("RGBA", (W, H), PAPER)
    draw = ImageDraw.Draw(image)
    draw.ellipse((-120, -80, 220, 200), fill=(255, 228, 214, 255))
    draw_header(draw, scene, index)
    shadow(image, (40, 120, 1880, 500))
    shadow(image, (40, 524, 1880, 1088))
    draw = ImageDraw.Draw(image)
    draw_step1(draw, scene)
    area = draw_step2_frame(draw, scene)
    drawers = {
        "stop": draw_stop_detail,
        "not_install": draw_not_install,
        "not_install_l2": draw_not_install_l2,
        "add_l1": draw_add_l1,
        "add_l2": draw_add_l2,
        "revise_l1": draw_revise_l1,
        "revise_l2": draw_revise_l2,
    }
    drawers[scene.kind](draw, area)
    if scene.next_title:
        text(draw, (1864, 1140), f"下一张：{scene.next_title}", font(22), MUTED, "rm")
    else:
        text(draw, (1864, 1140), "七张看完", font(22), MUTED, "rm")
    OUT_DIR.mkdir(exist_ok=True)
    dest = OUT_DIR / scene.filename
    temporary = dest.with_suffix(".png.tmp")
    image.convert("RGB").save(temporary, "PNG", optimize=True)
    temporary.replace(dest)
    return dest


def main() -> None:
    if OLD_POSTER.exists():
        OLD_POSTER.unlink()
    OUT_DIR.mkdir(exist_ok=True)
    keep = {scene.filename for scene in SCENES}
    for path in OUT_DIR.glob("*.png"):
        if path.name not in keep:
            try:
                path.unlink()
            except OSError:
                print(f"仍被打开，未能删掉：{path.name}")
    for index, scene in enumerate(SCENES, start=1):
        print(draw_scene(scene, index))


if __name__ == "__main__":
    main()
