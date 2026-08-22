"""使用帮助 vs 核价分析意图分流（规则优先，不调 LLM）。"""

from __future__ import annotations

from app.schemas.llm.analysis_query import QueryMode

# 查数 / 分析类口语（与 usage 同时出现时优先走 analysis）
_ANALYSIS_DATA_SIGNALS: tuple[str, ...] = (
    "多少钱",
    "多少元",
    "什么价",
    "价格多少",
    "单价多少",
    "环比",
    "趋势",
    "对比",
    "贵在哪",
    "涨幅",
    "贡献",
    "动因",
    "采购成本",
    "总成本",
    "总费用",
    "月总账",
    "怎么样",
    "情况如何",
    "报告",
    "一览",
    "存在吗",
    "有没有这个",
    "在不在",
)

_USAGE_HOW_SIGNALS: tuple[str, ...] = (
    "怎么用",
    "如何使用",
    "怎么操作",
    "如何操作",
    "怎么点",
    "怎样",
    "在哪",
    "哪里",
    "哪儿",
)

_USAGE_TOPIC_SIGNALS: tuple[str, ...] = (
    "看不到",
    "没有菜单",
    "菜单隐藏",
    "权限",
    "登录",
    "侧栏",
    "导航",
    "导出",
    "上传",
    "培训",
    "帮助",
    "教程",
    "步骤",
    "引擎",
    "检查就绪",
    "启动",
    "运行中",
    "卡住",
    "入门",
    "快速入门",
    "操作列",
    "材料清单",
    "bom",
    "BOM",
    "清单",
    "菜单",
    "每月",
    "月度",
)

_STUCK_SIGNALS: tuple[str, ...] = (
    "一直运行",
    "运行中",
    "卡住",
    "删任务",
    "删除任务",
)

_PERMISSION_SIGNALS: tuple[str, ...] = (
    "看不到",
    "没有菜单",
    "菜单隐藏",
    "无权限",
    "开通权限",
)

_HELP_TOPIC_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("engine", ("引擎", "自动核价", "检查就绪", "启动核价", "启动")),
    ("export", ("导出", "合册", "excel", "Excel", "核对合册")),
    ("faq_permission", _PERMISSION_SIGNALS),
    ("faq_stuck", _STUCK_SIGNALS),
    ("upload", ("上传", "导入", "怎么传")),
    ("bom_material", ("材料清单", "bom清单", "BOM清单", "清单在哪", "清单主线")),
    ("monthly", ("每月", "月度", "当月", "一个月要做")),
    ("list_usage", ("操作列", "列表只读", "明细按钮", "列表和上传")),
    ("menu", ("菜单", "侧栏", "导航", "冲压工程", "焊接工程", "一事一议")),
    ("start", ("入门", "登录", "第一次", "快速入门", "会话")),
)


def detect_query_mode(question: str) -> QueryMode:
    """判定走核价分析还是使用帮助。"""
    text = (question or "").strip()
    if not text:
        return "analysis"

    has_how = any(signal in text for signal in _USAGE_HOW_SIGNALS)
    has_usage_topic = any(signal in text for signal in _USAGE_TOPIC_SIGNALS)
    has_analysis = any(signal in text for signal in _ANALYSIS_DATA_SIGNALS)

    if has_analysis:
        return "analysis"

    if has_how:
        return "usage_help"

    if has_stuck_only(text) or has_permission_only(text):
        return "usage_help"

    if has_usage_topic:
        return "usage_help"

    return "analysis"


def detect_help_topic(question: str) -> str:
    """匹配 manifest 章节 id；无命中时回退 start。"""
    text = (question or "").strip().lower()
    if not text:
        return "start"

    best_id = "start"
    best_score = 0
    permission_bonus = 50 if has_permission_only(question) else 0
    stuck_bonus = 50 if has_stuck_only(question) else 0
    for topic_id, keywords in _HELP_TOPIC_RULES:
        topic_bonus = 0
        if topic_id == "faq_permission":
            topic_bonus = permission_bonus
        elif topic_id == "faq_stuck":
            topic_bonus = stuck_bonus
        for keyword in keywords:
            key = keyword.lower()
            if key in text or keyword in question:
                score = len(keyword) + topic_bonus
                if score > best_score:
                    best_score = score
                    best_id = topic_id

    return best_id


def has_stuck_only(text: str) -> bool:
    return any(signal in text for signal in _STUCK_SIGNALS)


def has_permission_only(text: str) -> bool:
    return any(signal in text for signal in _PERMISSION_SIGNALS)
