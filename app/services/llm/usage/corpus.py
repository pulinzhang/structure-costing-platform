"""从 static/helper 加载帮助语料（章节即检索单元）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from html import unescape
from pathlib import Path

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class CorpusChunk:
    """一条可检索的帮助语料。"""

    chunk_id: str
    title: str
    text: str
    source_page: str
    anchor: str
    keywords: tuple[str, ...]

    @property
    def help_url(self) -> str:
        return f"/helper/{self.source_page}#{self.anchor}"

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "chunk_id": self.chunk_id,
            "title": self.title,
            "text": self.text,
            "source_page": self.source_page,
            "anchor": self.anchor,
            "help_url": self.help_url,
            "keywords": list(self.keywords),
        }


def _helper_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "static" / "helper"


def _strip_html(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    text = unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _extract_section(html: str, section_id: str) -> str:
    pattern = re.compile(
        rf'<section\s+id="{re.escape(section_id)}"[^>]*>(.*?)</section>',
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(html)
    if not match:
        return ""
    return _strip_html(match.group(1))


def _read_helper_page(name: str) -> str:
    path = _helper_dir() / name
    return path.read_text(encoding="utf-8")


def _faq_chunks(faq_text: str) -> list[CorpusChunk]:
    chunks: list[CorpusChunk] = []
    if "看不到某个菜单" in faq_text:
        chunks.append(
            CorpusChunk(
                chunk_id="faq_permission",
                title="看不到菜单怎么办",
                text=(
                    "看不到某个菜单：找管理员在「设置 → 用户管理」开通权限后刷新页面。"
                    "侧栏与按钮均按权限码控制，无权限时菜单会隐藏。"
                ),
                source_page="help.html",
                anchor="faq",
                keywords=(
                    "看不到",
                    "没有菜单",
                    "菜单隐藏",
                    "权限",
                    "无权限",
                    "开通权限",
                    "焊接工程",
                    "侧栏",
                ),
            )
        )
    if "引擎一直运行中" in faq_text:
        chunks.append(
            CorpusChunk(
                chunk_id="faq_stuck",
                title="自动核价引擎任务卡住怎么办",
                text=(
                    "自动核价引擎一直显示运行中：本机异常关机可能导致任务卡住。"
                    "打开「核价 → 自动核价引擎」，在运行历史中删除该任务后重新启动。"
                    "删除用于清理中断任务，不会撤销已写入的钢材价、零件价或成品价。"
                ),
                source_page="help.html",
                anchor="faq",
                keywords=(
                    "运行中",
                    "一直运行",
                    "引擎",
                    "自动核价",
                    "运行历史",
                    "删任务",
                    "删除任务",
                ),
            )
        )
    if "成品核价计算卡住" in faq_text:
        chunks.append(
            CorpusChunk(
                chunk_id="faq_calc_stuck",
                title="成品核价计算卡住怎么办",
                text=(
                    "成品核价计算时若一直显示计算中、无法再次提交：通常是上一次异常中断"
                    "（关机、关浏览器），系统仍认为该范围正在计算。"
                    "打开「核价 → 成品核价计算」，在页面下方计算历史中找到状态为「计算中」的记录，"
                    "点删除释放锁，再重新开始计算。"
                    "仅删除日志与计算锁，不会撤销已写入成品核价一览的数据。"
                ),
                source_page="help.html",
                anchor="faq",
                keywords=(
                    "成品核价",
                    "成品价",
                    "成品成本",
                    "计算中",
                    "卡住",
                    "卡了",
                    "计算历史",
                    "删除",
                    "释放锁",
                    "重复提交",
                    "开始计算",
                ),
            )
        )
    if chunks:
        chunks.append(
            CorpusChunk(
                chunk_id="faq",
                title="操作问答",
                text=faq_text,
                source_page="help.html",
                anchor="faq",
                keywords=("帮助", "问答", "概念", "知识库", "样例"),
            )
        )
    return chunks


def _extra_faq_chunks() -> list[CorpusChunk]:
    """P1a 高频 FAQ：无独立 help 章节时补短答。"""
    return [
        CorpusChunk(
            chunk_id="upload",
            title="如何上传数据",
            text=(
                "上传入口在侧栏各模块的「上传」页：冲压工艺文件、冲次单价、材料清单、"
                "焊接单价、年度零件价、基准价与政策等。上传前确认基地、车型、清单版本、"
                "年月维度与本次核价一致；列表页只读核对，写入靠上传或计算页。"
            ),
            source_page="help.html",
            anchor="menu",
            keywords=("上传", "导入", "怎么传", "工艺文件", "材料清单"),
        ),
        CorpusChunk(
            chunk_id="bom_material",
            title="材料清单在哪里",
            text=(
                "材料清单在「焊接工程 → 材料清单列表」维护，它是整棵核价树的主数据。"
                "产品结构、结构图与清单列表共用同一套 BOM 数据；其它菜单多为给树上的节点挂价钱。"
            ),
            source_page="help.html",
            anchor="menu",
            keywords=(
                "材料清单",
                "bom",
                "BOM",
                "清单",
                "清单在哪",
                "清单主线",
                "产品结构",
            ),
        ),
        CorpusChunk(
            chunk_id="list_usage",
            title="列表页怎么用",
            text=(
                "列表页负责查询、审核与导出；上传/计算页负责写入。"
                "打开明细、编辑或删除请用操作列按钮，不要点整行。"
                "无导出权限时导出按钮会隐藏或提示。"
            ),
            source_page="help.html",
            anchor="start",
            keywords=("操作列", "列表只读", "明细按钮", "列表和上传", "导出"),
        ),
    ]


@lru_cache(maxsize=1)
def load_corpus_chunks() -> tuple[CorpusChunk, ...]:
    """加载 P1a 语料：help 四段 + knowledge 月度 + 高频 FAQ。"""
    help_html = _read_helper_page("help.html")
    knowledge_html = _read_helper_page("knowledge.html")

    chunks: list[CorpusChunk] = [
        CorpusChunk(
            chunk_id="start",
            title="快速入门",
            text=_extract_section(help_html, "start"),
            source_page="help.html",
            anchor="start",
            keywords=("入门", "登录", "第一次", "快速入门", "会话", "侧栏", "导航"),
        ),
        CorpusChunk(
            chunk_id="menu",
            title="菜单地图",
            text=_extract_section(help_html, "menu"),
            source_page="help.html",
            anchor="menu",
            keywords=(
                "菜单",
                "侧栏",
                "导航",
                "冲压工程",
                "焊接工程",
                "一事一议",
                "核价",
                "设置",
            ),
        ),
        CorpusChunk(
            chunk_id="engine",
            title="自动核价引擎",
            text=_extract_section(help_html, "engine"),
            source_page="help.html",
            anchor="engine",
            keywords=(
                "引擎",
                "自动核价",
                "检查就绪",
                "启动核价",
                "启动",
                "运行",
                "怎么跑",
            ),
        ),
        CorpusChunk(
            chunk_id="export",
            title="导出 Excel",
            text=_extract_section(help_html, "export"),
            source_page="help.html",
            anchor="export",
            keywords=("导出", "合册", "excel", "Excel", "核对合册", "导出 Excel"),
        ),
        CorpusChunk(
            chunk_id="monthly",
            title="每月核价要做什么",
            text=_extract_section(knowledge_html, "month"),
            source_page="knowledge.html",
            anchor="month",
            keywords=("每月", "月度", "当月", "一个月要做", "维护", "哪些数据"),
        ),
    ]

    faq_text = _extract_section(help_html, "faq")
    chunks.extend(_faq_chunks(faq_text))
    chunks.extend(_extra_faq_chunks())

    return tuple(chunk for chunk in chunks if chunk.text.strip())
