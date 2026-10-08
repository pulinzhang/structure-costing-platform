"""12-page product briefing. Value versus Excel manual work.

Conversion deck is build_gm_intro_pptx.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_gm_intro_pptx as deck
from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Inches

deck.SLIDE_COUNT = 12

W = deck.W
H = deck.H
ORANGE = deck.ORANGE
INK = deck.INK
WHITE = deck.WHITE
SOFT = deck.SOFT
MUTED = deck.MUTED
DIM = deck.DIM
SAND = deck.SAND
LINE = deck.LINE
FONT_EN = deck.FONT_EN
COMPANY = deck.COMPANY
APP_NAME = deck.APP_NAME
APP_NAME_SHORT = deck.APP_NAME_SHORT


def make() -> Path:
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    blank = prs.slide_layouts[6]
    t = deck.textbox
    card = deck.card
    kicker = deck.kicker
    title = deck.title_block
    footer = deck.footer
    dark_footer = deck.dark_footer
    hline = deck.hline
    rect = deck.rect

    # 01 封面：价值相对 Excel；两本价不能相减当毛利
    s = prs.slides.add_slide(blank)
    deck.paint_dark(s)
    t(
        s,
        Inches(0.7),
        Inches(0.42),
        Inches(6),
        Inches(0.36),
        COMPANY,
        size=16,
        color=WHITE,
        bold=True,
        spacing=40,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    hline(s, Inches(0.7), Inches(1.28), Inches(1.6), ORANGE, 2.25)
    t(
        s,
        Inches(0.7),
        Inches(1.48),
        Inches(12),
        Inches(0.32),
        "客户买的是价值",
        size=14,
        color=ORANGE,
    )
    t(
        s,
        Inches(0.7),
        Inches(2.0),
        Inches(12),
        Inches(1.0),
        APP_NAME,
        size=40,
        color=WHITE,
        bold=True,
    )
    t(
        s,
        Inches(0.7),
        Inches(3.25),
        Inches(11.4),
        Inches(1.6),
        "比继续用 Excel 手工：\n少耗人，两本价各算清，对账有据。",
        size=22,
        color=SOFT,
        line_pt=36,
    )
    dark_footer(s, 1)

    # 02 价值只认三样
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "01   VALUE")
    title(s, "价值，是比 Excel 多保住的结果")
    t(
        s,
        Inches(0.7),
        Inches(1.5),
        Inches(12),
        Inches(0.5),
        "每月只认三样：少耗的人、两本价各算清、少打的架。",
        size=16,
        color=MUTED,
    )
    pillars = [
        ("人的时间", "少占熟练人员好几天。\n人请假，两本账照样出。\n省下的是最缺的人。"),
        ("两本价", "开给奇瑞的是焊完的总成。\n付给二级商的是分总成。\n中间是公司自己的焊接。"),
        ("对账的工夫", "文件、人和版本留在平台。\n对奇瑞、二级商和财务，\n不必再开会统一口径。"),
    ]
    for i, (head, body) in enumerate(pillars):
        x = Inches(0.7 + i * 4.15)
        card(s, x, Inches(2.2), Inches(3.95), Inches(4.35))
        t(
            s,
            x + Inches(0.28),
            Inches(2.5),
            Inches(3.4),
            Inches(0.7),
            head,
            size=22,
            color=INK,
            bold=True,
        )
        t(
            s,
            x + Inches(0.28),
            Inches(3.4),
            Inches(3.4),
            Inches(2.7),
            body,
            size=15,
            color=MUTED,
            line_pt=26,
        )
    footer(s, 2)

    # 03 对照表：现网相对 Excel，公司得到什么
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "02   VERSUS")
    title(s, "同样核价，Excel 和现网差在哪")
    headers = [(Inches(1.9), "Excel 手工"), (Inches(5.35), "现网"), (Inches(8.8), "公司得到")]
    for x, label in headers:
        t(
            s,
            x,
            Inches(1.48),
            Inches(3.3),
            Inches(0.28),
            label,
            size=12,
            color=ORANGE,
            spacing=60,
        )
    rows = [
        (
            "人",
            "熟练人员做好几天。\n人走，账就停。",
            "上传之后，引擎约 20 秒。\n规则留在平台。",
            "人转去谈价和异常。\n请假也不停账。",
        ),
        (
            "价",
            "总成、分总成各一张表。\n两本对不到一起。",
            "总成价、分总成价\n同一引擎，各算各的。",
            "焊费只计一次。\n协议按分总成签。",
        ),
        (
            "月",
            "钢价、BOM、工艺、设变\n散在文件夹。",
            "当月依据，\n当月一起计算。",
            "该调的开票价和采购价，\n当月跟上。",
        ),
        (
            "对",
            "私人拷贝。\n口径靠骨干记忆。",
            "文件、操作、当期版本\n都留着。",
            "对奇瑞、二级商、财务，\n拿记录对。",
        ),
    ]
    for i, (label, excel, now, gain) in enumerate(rows):
        y = Inches(1.86 + i * 1.22)
        rect(s, Inches(0.7), y, Inches(11.93), Inches(1.12), WHITE, LINE)
        rect(s, Inches(0.7), y, Inches(0.055), Inches(1.12), ORANGE)
        t(
            s,
            Inches(0.9),
            y + Inches(0.28),
            Inches(0.85),
            Inches(0.55),
            label,
            size=20,
            color=INK,
            bold=True,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        t(
            s,
            Inches(1.9),
            y + Inches(0.16),
            Inches(3.25),
            Inches(0.82),
            excel,
            size=14,
            color=MUTED,
            line_pt=22,
        )
        t(
            s,
            Inches(5.35),
            y + Inches(0.16),
            Inches(3.25),
            Inches(0.82),
            now,
            size=14,
            color=INK,
            line_pt=22,
        )
        t(
            s,
            Inches(8.8),
            y + Inches(0.16),
            Inches(3.55),
            Inches(0.82),
            gain,
            size=14,
            color=INK,
            bold=True,
            line_pt=22,
        )
    footer(s, 3)

    # 04 四项结果从哪来
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "03   WHERE")
    title(s, "这四项结果，从同一套规则里来")
    t(
        s,
        Inches(0.7),
        Inches(1.5),
        Inches(12),
        Inches(0.45),
        "依据仍由人上传。耗掉好几天的，是其后的计算、对表和解释。",
        size=16,
        color=MUTED,
    )
    steps = [
        ("01", "依据进入", "钢价政策、BOM、\n工艺和工程变更，\n按月纳入。"),
        ("02", "引擎计算", "总成价与采购价，\n同一套规则。\n约 20 秒。"),
        ("03", "协议落地", "采购协议按结果出。\n不必再抄一版表。"),
        ("04", "只解释", "AI 讲涨跌原因。\n价格只认引擎。"),
    ]
    for i, (num, head, body) in enumerate(steps):
        x = Inches(0.7 + i * 3.15)
        card(s, x, Inches(2.2), Inches(3.0), Inches(4.35))
        t(
            s,
            x + Inches(0.24),
            Inches(2.48),
            Inches(2.5),
            Inches(0.32),
            num,
            size=13,
            color=ORANGE,
            font=FONT_EN,
            spacing=80,
        )
        t(
            s,
            x + Inches(0.24),
            Inches(3.0),
            Inches(2.5),
            Inches(0.9),
            head,
            size=22,
            color=INK,
            bold=True,
        )
        t(
            s,
            x + Inches(0.24),
            Inches(4.1),
            Inches(2.5),
            Inches(2.0),
            body,
            size=15,
            color=MUTED,
            line_pt=26,
        )
    footer(s, 4)

    # 05 人
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "04   PEOPLE")
    title(s, "熟练人员不必再耗在做表上")
    card(s, Inches(0.7), Inches(1.7), Inches(5.7), Inches(4.85))
    t(s, Inches(1.05), Inches(2.0), Inches(5), Inches(0.3), "Excel 手工", size=13, color=DIM)
    t(
        s,
        Inches(1.05),
        Inches(2.5),
        Inches(5.1),
        Inches(1.15),
        "熟练人员\n好几天",
        size=32,
        color=INK,
        bold=True,
        line_pt=42,
    )
    t(
        s,
        Inches(1.05),
        Inches(4.35),
        Inches(4.95),
        Inches(1.8),
        "一事一议、总成、采购对象，\n都压在这几天里。\n人一走，账就停。",
        size=15,
        color=MUTED,
        line_pt=26,
    )
    card(s, Inches(6.9), Inches(1.7), Inches(5.7), Inches(4.85))
    t(s, Inches(7.25), Inches(2.0), Inches(5), Inches(0.3), "现网", size=13, color=ORANGE)
    t(
        s,
        Inches(7.25),
        Inches(2.5),
        Inches(5.1),
        Inches(1.15),
        "上传之后\n约 20 秒",
        size=32,
        color=INK,
        bold=True,
        line_pt=42,
    )
    t(
        s,
        Inches(7.25),
        Inches(4.35),
        Inches(5.0),
        Inches(1.8),
        "规则在引擎里。\n同样的人去谈价、看异常。\n能力留在公司，不在个人身上。",
        size=15,
        color=MUTED,
        line_pt=26,
    )
    footer(s, 5)

    # 06 两本价
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "05   WELD")
    title(s, "买的是分总成，卖的是焊完的总成")
    books = [
        ("卖出", "焊完的总成", "开给奇瑞的是总成。\n谈价、开票看这一本。"),
        ("买入", "分总成", "付给二级商的是分总成。\n买回来还要再焊。"),
        ("中间", "公司焊接", "分总成要焊成总成。\n这一截是焊接，不是毛利。"),
    ]
    for i, (tag, head, body) in enumerate(books):
        x = Inches(0.7 + i * 4.15)
        card(s, x, Inches(1.7), Inches(3.95), Inches(4.85))
        t(s, x + Inches(0.28), Inches(2.05), Inches(3.4), Inches(0.32), tag, size=13, color=ORANGE)
        t(
            s,
            x + Inches(0.28),
            Inches(2.55),
            Inches(3.4),
            Inches(1.1),
            head,
            size=26,
            color=INK,
            bold=True,
        )
        t(
            s,
            x + Inches(0.28),
            Inches(3.9),
            Inches(3.4),
            Inches(2.1),
            body,
            size=16,
            color=MUTED,
            line_pt=26,
        )
    footer(s, 6)

    # 07 当月
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "06   MONTH")
    title(s, "价跟着当月的事实走")
    card(s, Inches(0.7), Inches(1.7), Inches(5.7), Inches(4.85))
    t(s, Inches(1.05), Inches(2.05), Inches(5), Inches(0.3), "Excel 手工", size=13, color=DIM)
    t(
        s,
        Inches(1.05),
        Inches(2.55),
        Inches(5.1),
        Inches(1.2),
        "价晚一步",
        size=32,
        color=INK,
        bold=True,
    )
    t(
        s,
        Inches(1.05),
        Inches(4.0),
        Inches(4.95),
        Inches(2.1),
        "钢价变了，设变来了。\n表还停在文件夹里。\n该向奇瑞调的，晚了一个月。\n该向二级商调的，也晚了。",
        size=15,
        color=MUTED,
        line_pt=26,
    )
    card(s, Inches(6.9), Inches(1.7), Inches(5.7), Inches(4.85))
    t(s, Inches(7.25), Inches(2.05), Inches(5), Inches(0.3), "现网", size=13, color=ORANGE)
    t(
        s,
        Inches(7.25),
        Inches(2.55),
        Inches(5.1),
        Inches(1.2),
        "当月算当月",
        size=32,
        color=INK,
        bold=True,
    )
    t(
        s,
        Inches(7.25),
        Inches(4.0),
        Inches(5.0),
        Inches(2.1),
        "钢价、BOM、工艺、设变，\n进入当月一起算。\n开票价和采购价一起跟上。",
        size=15,
        color=MUTED,
        line_pt=26,
    )
    footer(s, 7)

    # 08 对账
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "07   TRACE")
    title(s, "对得上，就不必再开会扯皮")
    traces = [
        ("哪份文件", "当时用的 Excel 能找回。省下的是翻私人拷贝。"),
        ("谁操作的", "上传、计算、变更有日志。责任落得到人。"),
        ("当期哪版", "钢价、BOM、工艺、设变按月对齐。不会用错月。"),
        ("同一套规则", "总成价、分总成价同一引擎，各算各的。\n焊费计在总成上，不重复计。"),
    ]
    for i, (head, body) in enumerate(traces):
        col, row = i % 2, i // 2
        x = Inches(0.7 + col * 6.3)
        y = Inches(1.65 + row * 2.5)
        card(s, x, y, Inches(6.05), Inches(2.28))
        t(
            s,
            x + Inches(0.32),
            y + Inches(0.38),
            Inches(5.4),
            Inches(0.5),
            head,
            size=22,
            color=INK,
            bold=True,
        )
        t(
            s,
            x + Inches(0.32),
            y + Inches(1.1),
            Inches(5.4),
            Inches(0.85),
            body,
            size=16,
            color=MUTED,
            line_pt=26,
        )
    footer(s, 8)

    # 09 看懂的成本
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "08   ANSWER")
    title(s, "看懂涨跌，不用再等做表的人")
    t(
        s,
        Inches(0.7),
        Inches(1.48),
        Inches(12),
        Inches(0.4),
        "数字由引擎计算。AI 只讲原因。约 30 秒抓住问题、关键数字和核对线索。",
        size=16,
        color=MUTED,
    )
    questions = [
        "这个月总成开给奇瑞的价，为什么涨了？",
        "向二级商采购的对象，哪些涨幅最大？",
        "工程变更之后，开票价和采购价各动了多少？",
        "这个总成和上个月差在哪里？",
        "把本月成本变化整理一下。",
    ]
    for i, q in enumerate(questions):
        y = Inches(2.0 + i * 0.9)
        rect(s, Inches(0.7), y, Inches(11.93), Inches(0.8), WHITE, LINE)
        rect(s, Inches(0.7), y, Inches(0.055), Inches(0.8), ORANGE)
        t(
            s,
            Inches(1.05),
            y + Inches(0.14),
            Inches(0.7),
            Inches(0.5),
            f"Q{i + 1}",
            size=12,
            color=ORANGE,
            font=FONT_EN,
            anchor=MSO_ANCHOR.MIDDLE,
        )
        t(
            s,
            Inches(1.9),
            y + Inches(0.14),
            Inches(10.3),
            Inches(0.5),
            q,
            size=17,
            color=INK,
            anchor=MSO_ANCHOR.MIDDLE,
        )
    footer(s, 9)

    # 10 问一句的路径
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "09   ASK")
    title(s, "问一句为什么涨，人只负责开口")
    before = ["人找 Excel", "找数据", "找公式", "做分析", "等人下结论"]
    after = ["直接问", "系统取当月数", "引擎计算", "AI 讲原因"]
    t(s, Inches(0.7), Inches(1.55), Inches(5.5), Inches(0.32), "Excel 手工", size=13, color=DIM)
    t(s, Inches(7.1), Inches(1.55), Inches(5.5), Inches(0.32), "现网", size=13, color=ORANGE)
    for i, label in enumerate(before):
        y = Inches(1.95 + i * 0.9)
        rect(s, Inches(0.7), y, Inches(5.5), Inches(0.78), SAND, LINE)
        t(
            s,
            Inches(1.0),
            y + Inches(0.14),
            Inches(4.9),
            Inches(0.5),
            f"{i + 1:02d}    {label}",
            size=16,
            color=MUTED,
            anchor=MSO_ANCHOR.MIDDLE,
        )
    for i, label in enumerate(after):
        y = Inches(1.95 + i * 1.12)
        rect(s, Inches(7.1), y, Inches(5.5), Inches(0.98), WHITE, LINE)
        rect(s, Inches(7.1), y, Inches(5.5), Inches(0.045), ORANGE)
        t(
            s,
            Inches(7.45),
            y + Inches(0.22),
            Inches(4.9),
            Inches(0.54),
            f"{i + 1:02d}    {label}",
            size=18,
            color=INK,
            bold=True,
            anchor=MSO_ANCHOR.MIDDLE,
        )
    footer(s, 10)

    # 11 价值交到岗位
    s = prs.slides.add_slide(blank)
    deck.paint_light(s)
    kicker(s, "10   WHO")
    title(s, "价值交到三个岗位上")
    roles = [
        ("采购", "该付的是分总成，看这一本。\n协议按结果出，不必再抄表。"),
        ("财务", "总成开票、分总成应付，\n各有一本。焊费不重复计。"),
        ("管理人员", "涨了为什么、差在哪里，\n直接问，不必等骨干。"),
    ]
    for i, (head, body) in enumerate(roles):
        x = Inches(0.7 + i * 4.15)
        card(s, x, Inches(1.7), Inches(3.95), Inches(4.85))
        t(
            s,
            x + Inches(0.28),
            Inches(2.15),
            Inches(3.4),
            Inches(0.36),
            f"{i + 1:02d}",
            size=13,
            color=ORANGE,
            font=FONT_EN,
            spacing=80,
        )
        t(
            s,
            x + Inches(0.28),
            Inches(2.7),
            Inches(3.4),
            Inches(0.7),
            head,
            size=26,
            color=INK,
            bold=True,
        )
        t(
            s,
            x + Inches(0.28),
            Inches(3.7),
            Inches(3.4),
            Inches(2.2),
            body,
            size=16,
            color=MUTED,
            line_pt=26,
        )
    footer(s, 11)

    # 12 收束
    s = prs.slides.add_slide(blank)
    deck.paint_dark(s)
    hline(s, Inches(0.7), Inches(1.35), Inches(1.6), ORANGE, 2.25)
    t(
        s,
        Inches(0.7),
        Inches(1.58),
        Inches(12),
        Inches(0.32),
        "WHAT THEY BUY",
        size=13,
        color=ORANGE,
        font=FONT_EN,
        spacing=160,
    )
    t(
        s,
        Inches(0.7),
        Inches(2.1),
        Inches(12),
        Inches(2.3),
        "人可以交接。焊费只计一次。\n当月价当月算。对账有据。",
        size=32,
        color=WHITE,
        bold=True,
        line_pt=48,
    )
    t(
        s,
        Inches(0.7),
        Inches(4.7),
        Inches(12),
        Inches(1.15),
        "这是相对 Excel 手工，客户买走的价值。\n熟练人员好几天的计算，上传依据后约 20 秒。",
        size=18,
        color=SOFT,
        line_pt=30,
    )
    dark_footer(s, 12)

    out = Path(__file__).resolve().parents[1] / "docs" / f"{APP_NAME}-产品介绍.pptx"
    prs.save(str(out))
    return out


if __name__ == "__main__":
    path = make()
    print(path)
