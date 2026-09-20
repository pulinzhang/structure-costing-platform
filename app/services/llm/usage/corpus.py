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
                    "删除用于清理中断任务，不会撤销已写入的钢材价、零件价或总成价。"
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
                    "总成核价（旧称成品核价）计算时若一直显示计算中、无法再次提交：通常是上一次异常中断"
                    "（关机、关浏览器），系统仍认为该范围正在计算。"
                    "打开「核价 → 总成核价计算」（即成品核价计算页），在页面下方计算历史中找到状态为「计算中」的记录，"
                    "点删除释放锁，再重新开始计算。"
                    "仅删除日志与计算锁，不会撤销已写入总成核价一览的数据。"
                ),
                source_page="help.html",
                anchor="faq",
                keywords=(
                    "成品核价",
                    "成品价",
                    "成品成本",
                    "总成核价",
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
            chunk_id="faq_procurement_fee",
            title="采购对象的费用在哪看",
            text=(
                "「焊接工程 → 采购对象」只管集合：买哪些、外发还是自制、供应商是谁，"
                "清单行没有费用字段，也没有按年裁剪；问「采购对象的费用是多少」系统答不出金额是正常的。"
                "要看钱请改问法："
                "① 单件价直接问「2856的价格多少」或「T13J 某某总成多少钱」（读总成核价卡）；"
                "② 按供应商签二级厂、横排月列结算价：打开一级菜单「采购价格协议」"
                "（采购对象视图一家一导；总成视图整包一份）。"
                "协议金额抄总成核价已算的应成本，须先算总成核价。"
            ),
            source_page="help.html",
            anchor="faq",
            keywords=(
                "采购对象的费用",
                "采购对象费用",
                "采购对象多少钱",
                "采购对象价格",
                "采购对象结算价",
                "采购对象总成本",
                "采购对象总费用",
            ),
        ),
        CorpusChunk(
            chunk_id="faq_ec_costing_effect_month",
            title="设变后哪个月用新号",
            text=(
                "设变从哪个月开始算新零件 / 新总成：看变更单上的**生效月**。"
                "生效月及以后按新号核价；生效前一个月及更早仍按旧号。"
                "这个月核价用旧号还是新号：把账期和生效月比一下即可。"
                "设变当月新旧零件可以各有一张卡：旧号用到生效前一月，新号从生效月起。"
                "旧零件过期了还能不能出协议 / 签约：协议按账期只带仍有效的件，已到期旧号不进签约清单。"
                "设变回滚了 / 删了变更：整本删除后当没做过，核价只认当前账期仍有效的件。"
                "增加零件进采购对象后：厂家要自己填；系统不自动抄供应商，外发须确认并指定厂家。"
            ),
            source_page="help.html",
            anchor="faq",
            keywords=(
                "哪个月开始",
                "哪个月用新号",
                "用旧号还是新号",
                "旧零件还能",
                "新旧并存",
                "过期还能签",
                "过期了还能不能出协议",
                "过期了还能",
                "回滚",
                "删了变更",
                "生效月怎么算",
                "设变从哪个月",
                "厂家要不要自己填",
            ),
        ),
        CorpusChunk(
            chunk_id="faq_ec_tree_vs_procurement",
            title="为什么新版本采购对象比变更单多",
            text=(
                "为什么新版本采购对象有 17 个，而变更单只有 5 条？"
                "因为这两个数字统计的不是同一件事。"
                "变更单记录的是本次工程变更的变化条数；本例有 5 条，"
                "系统再判断哪些树坑需要换树或停止。"
                "本例 1 棵交货总成完成停止（旧树到期，不再种新树，历史仍在），"
                "4 棵交货总成换成了新树。"
                "换树是在材料清单序号这个树坑上拿掉旧交货总成、种入完整新树，"
                "不是只改 Excel 写到的零件。没有改变的零件继续用原零件号，"
                "变化或新增的零件用新号，但它们现在都在同一棵新树上。"
                "新树整体属于材料清单版本，例如 EC-202507。"
                "版本章说明这棵树属于哪个版本，不是说明哪些零件被改过。"
                "所以筛选 EC-202507 时，列出的是这 4 棵新树里全部采购对象，"
                "包括没有换号、只是从旧树继承过来的采购件。"
                "4 是树的数量。17 是这 4 棵新树里面采购对象的数量。"
                "数字不同是正常的。17 不是「这次新增或修改了 17 个零件」，"
                "而是「这 4 棵新树当前共有 17 个采购对象」。"
            ),
            source_page="help.html",
            anchor="faq",
            keywords=(
                "新版本采购对象",
                "采购对象怎么这么多",
                "采购对象有17",
                "采购对象有 17",
                "变更单只有",
                "换了几棵",
                "树的数量",
                "树里面采购对象",
                "为什么这么多采购对象",
                "采购对象比变更单多",
            ),
        ),
        CorpusChunk(
            chunk_id="part_lookup_how",
            title="怎么用零件号或简码问价",
            text=(
                "问某个件多少钱，直接在助理里打零件号或后几位即可，例如「2856的价格多少」"
                "「8898在不在库里」。不必先写全码，也不必先选年月；系统按核价表最新年月取卡。"
                "分总成/冲压件的价格和供货总成不是同一张卡，不要混在一起对账。"
                "这是查已核算结果，不是去计算页改价。计算仍走各模块计算页。"
            ),
            source_page="help.html",
            anchor="start",
            keywords=(
                "简码",
                "短码",
                "后四位",
                "怎么查价",
                "怎么问价",
                "零件号怎么问",
                "2856",
            ),
        ),
        CorpusChunk(
            chunk_id="upload",
            title="如何上传数据",
            text=(
                "上传入口在侧栏各模块的「上传」页：冲压工艺文件、模具布点、冲次单价、检具费、"
                "材料清单、焊接单价、包装运输、年度零件价、基准价与加减价政策等。"
                "投产后改图换号请走「工程变更 → 上传工程变更」，不要在材料清单/工艺/布点页整包覆盖新号。"
                "上传前确认基地、项目、清单版本、年月维度与本次核价一致；列表页只读核对，写入靠上传或计算页。"
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
        CorpusChunk(
            chunk_id="die_gauge",
            title="模具费和检具费怎么用",
            text=(
                "冲压工程里维护模具布点、模具单价、年度模具费，以及检具费档案。"
                "零件核价直接成本 = 原材料净成本 + 加工费 + 模具费 + 检具费；零件价页无档案时费用为 0、不自动补算。"
                "自动核价引擎：有布点且当年无模具费结果则自动补算；缺生效模具单价硬停；检具费不补算。"
                "家模副产品不算模具费。"
            ),
            source_page="help.html",
            anchor="stamping",
            keywords=("模具费", "检具费", "模具布点", "模具单价", "检具"),
        ),
        CorpusChunk(
            chunk_id="procurement",
            title="采购对象清单在哪里",
            text=(
                "采购对象在「焊接工程 → 采购对象」：从材料清单生成集合。"
                "列入退化供货件、分总成、冲压件；标准件/胶等与异常进核对区。"
                "有子件的供货总成永不列入。列表可确认外发/自制、指定供应商。不管价。"
                "要月度结算价、导出《批量零部件价格协议》请去「采购价格协议」。"
            ),
            source_page="help.html",
            anchor="welding",
            keywords=("采购对象", "外发", "自制", "供应商", "退化供货件"),
        ),
        CorpusChunk(
            chunk_id="assembly_cost",
            title="总成核价（成品核价）在哪",
            text=(
                "核价菜单「总成核价」核算材料清单根节点（供货总成 / 成品）的月总账与总费用。"
                "计算页 #/assembly-cost-calc，一览 #/assembly-cost。旧称成品核价 / L0。"
                "卡住时在计算历史里删除「计算中」记录释放锁。"
            ),
            source_page="help.html",
            anchor="costing-pages",
            keywords=("总成核价", "成品核价", "L0", "总成核价计算", "成品核价计算"),
        ),
        CorpusChunk(
            chunk_id="procurement_contract_report",
            title="采购价格协议在哪",
            text=(
                "一级菜单「采购价格协议」给二级厂签《批量零部件价格协议》。"
                "页 #/procurement-contract-report，在核价之后、文件溯源之前。"
                "只读查询 + 导出协议，不算价、不落结果表。先算总成核价才有结算价。"
                "双按钮切视图：默认「采购对象」可筛供应商、一家一导；「总成」不筛供应商、整包一份、乙方现场填。"
                "窗口最多 12 个月；打开默认最近一次核价的单月。缺结算价显示斜杠。"
                "采购对象视图须先生成焊接工程里的采购对象清单；总成视图不依赖清单。"
            ),
            source_page="help.html",
            anchor="procurement-contract-report",
            keywords=(
                "采购价格协议",
                "采购价格",
                "批量零部件价格协议",
                "价格协议",
                "导出协议",
                "签约",
                "二级厂",
                "总成视图",
            ),
        ),
        CorpusChunk(
            chunk_id="audit",
            title="列表怎么审核",
            text=(
                "审核在各结果列表页操作列：总成核价一览、冲压零件价格一览、焊接费列表、"
                "冲压模具费列表、采购对象清单。待审核行可点审核；已审核可按权限反审核。"
                "列表页只改审核状态，不算价。问「还有多少待审核」请用智能体查数，不要只问怎么点。"
            ),
            source_page="help.html",
            anchor="start",
            keywords=("怎么审核", "如何审核", "反审核", "审核按钮", "待审核"),
        ),
        CorpusChunk(
            chunk_id="calc_run",
            title="计算页在哪",
            text=(
                "写入靠计算页，不在一览上改价。"
                "冲压零件价格计算 #/stamping-part-cost-calc；"
                "总成核价计算 #/assembly-cost-calc；"
                "冲压模具费计算 #/stamping-die-fee-calc；"
                "冲压加工费计算在冲压工程计算页；"
                "焊接费计算 #/bom-welding-fee-calc。"
                "算完后到对应一览核对并审核。"
            ),
            source_page="help.html",
            anchor="costing-pages",
            keywords=(
                "冲压零件价格计算",
                "总成核价计算",
                "模具费计算",
                "加工费计算",
                "焊接费计算",
                "计算页",
                "怎么计算",
                "怎么算模具费",
            ),
        ),
        CorpusChunk(
            chunk_id="yishiyiyi_extra",
            title="中标钢厂厚度价格一览",
            text=(
                "一事一议 → 中标钢厂厚度价格一览表：选定年/月/基地后预览或导出中标基价叠厚度加减价，不改核价库。"
            ),
            source_page="help.html",
            anchor="yishiyiyi",
            keywords=("中标", "厚度价格", "中标钢厂"),
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
                "工程变更",
                "一事一议",
                "主数据",
                "核价",
                "文件溯源",
                "设置",
            ),
        ),
        CorpusChunk(
            chunk_id="stamping",
            title="冲压工程怎么用",
            text=_extract_section(help_html, "stamping"),
            source_page="help.html",
            anchor="stamping",
            keywords=("冲压工程", "冲压工艺", "冲次单价", "冲压加工费", "模具", "检具"),
        ),
        CorpusChunk(
            chunk_id="welding",
            title="焊接工程怎么用",
            text=_extract_section(help_html, "welding"),
            source_page="help.html",
            anchor="welding",
            keywords=("焊接工程", "焊接单价", "焊接拆解", "焊接费", "包装运输", "采购对象"),
        ),
        CorpusChunk(
            chunk_id="engineering-change",
            title="工程变更怎么用",
            text=_extract_section(help_html, "engineering-change"),
            source_page="help.html",
            anchor="engineering-change",
            keywords=(
                "工程变更",
                "改图",
                "此件不装",
                "完成停止",
                "增加零件",
                "换号",
                "设变",
                "变更单",
                "零件汇总",
                "材料清单换号",
            ),
        ),
        CorpusChunk(
            chunk_id="yishiyiyi",
            title="一事一议怎么用",
            text=_extract_section(help_html, "yishiyiyi"),
            source_page="help.html",
            anchor="yishiyiyi",
            keywords=("一事一议", "基准价", "加减价", "废料", "中标钢厂"),
        ),
        CorpusChunk(
            chunk_id="costing-pages",
            title="核价模块怎么用",
            text=_extract_section(help_html, "costing-pages"),
            source_page="help.html",
            anchor="costing-pages",
            keywords=("钢材联动", "冲压零件价格", "总成核价", "成品核价"),
        ),
        CorpusChunk(
            chunk_id="file_trace",
            title="文件溯源",
            text=_extract_section(help_html, "file-trace"),
            source_page="help.html",
            anchor="file-trace",
            keywords=("文件溯源", "原件", "上传记录", "溯源"),
        ),
        CorpusChunk(
            chunk_id="masterdata",
            title="主数据怎么用",
            text=_extract_section(help_html, "masterdata"),
            source_page="help.html",
            anchor="masterdata",
            keywords=("主数据", "牌号分类", "冷轧", "镀锌", "酸洗"),
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
            keywords=("导出", "excel", "Excel", "月度核对导出", "导出 Excel", "导出协议"),
        ),
        CorpusChunk(
            chunk_id="monthly",
            title="每月核价要做什么",
            text=_extract_section(knowledge_html, "month"),
            source_page="knowledge.html",
            anchor="month",
            keywords=("每月", "月度", "当月", "一个月要做", "维护", "哪些数据"),
        ),
        CorpusChunk(
            chunk_id="engineering_change_knowledge",
            title="工程变更核价口径",
            text=_extract_section(knowledge_html, "engineering-change"),
            source_page="knowledge.html",
            anchor="engineering-change",
            keywords=(
                "生效月",
                "到期月",
                "新旧并存",
                "哪个月开始",
                "用旧号还是新号",
                "旧零件还能",
                "过期还能签",
                "时间轴",
                "切点",
                "树坑",
                "换树",
            ),
        ),
        CorpusChunk(
            chunk_id="procurement_knowledge",
            title="采购对象列入规则",
            text=_extract_section(knowledge_html, "procurement"),
            source_page="knowledge.html",
            anchor="procurement",
            keywords=("采购对象", "退化供货件", "列入", "标准件"),
        ),
    ]

    faq_text = _extract_section(help_html, "faq")
    chunks.extend(_faq_chunks(faq_text))
    chunks.extend(_extra_faq_chunks())

    return tuple(chunk for chunk in chunks if chunk.text.strip())
