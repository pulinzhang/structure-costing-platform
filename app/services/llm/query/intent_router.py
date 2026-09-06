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
    "的情况",
    "存在吗",
    "有没有这个",
    "在不在",
)

# 「缺口」口语：还差/缺什么（勿单独用「哪些数据」，否则会误伤「每月要维护哪些数据」）
_ENGINE_GAP_SIGNALS: tuple[str, ...] = (
    "还差",
    "缺什么",
    "少了什么",
    "还要什么",
    "还需要",
    "缺少什么",
    "缺哪些",
    "缺哪些数据",
    "还差什么",
    "还差那些",
    "数据齐",
    "齐了吗",
    "准备什么",
    "上传什么",
)

# 「核算动作」：须与缺口词同现；禁止单独用「数据」（太宽）
_ENGINE_COSTING_SIGNALS: tuple[str, ...] = (
    "核算",
    "核价",
    "自动核价",
    "引擎",
    "检查就绪",
    "能算",
    "可以算",
    "能不能算",
    "才可以",
    "才能",
)

_USAGE_HOW_SIGNALS: tuple[str, ...] = (
    "怎么",
    "怎么用",
    "如何使用",
    "怎么操作",
    "如何操作",
    "怎么点",
    "怎样",
    "怎么办",
    "如何",
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
    "总成核价",
    "成品核价",
    "文件溯源",
    "采购对象",
    "模具费",
    "检具费",
    "牌号分类",
)

_STUCK_SIGNALS: tuple[str, ...] = (
    "一直运行",
    "运行中",
    "卡住",
    "删任务",
    "删除任务",
)

_CALC_STUCK_SIGNALS: tuple[str, ...] = (
    "成品核价",
    "成品价",
    "成品成本",
    "l0核价",
    "总成核价",
)

_CALC_STUCK_STATE_SIGNALS: tuple[str, ...] = (
    "卡住",
    "卡了",
    "计算中",
    "一直算",
    "重复提交",
    "释放锁",
    "计算历史",
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
    ("faq_calc_stuck", _CALC_STUCK_SIGNALS + _CALC_STUCK_STATE_SIGNALS),
    ("upload", ("上传", "导入", "怎么传")),
    ("bom_material", ("材料清单", "bom清单", "BOM清单", "清单在哪", "清单主线")),
    ("monthly", ("每月", "月度", "当月", "一个月要做")),
    ("list_usage", ("操作列", "列表只读", "明细按钮", "列表和上传")),
    ("die_gauge", ("模具费", "检具费", "模具布点", "模具单价", "检具")),
    ("procurement", ("采购对象", "外发", "退化供货件")),
    ("file_trace", ("文件溯源", "溯源")),
    ("assembly_cost", ("总成核价", "成品核价计算", "总成核价计算")),
    ("yishiyiyi_extra", ("牌号分类", "中标钢厂", "厚度价格一览")),
    ("menu", ("菜单", "侧栏", "导航", "冲压工程", "焊接工程", "一事一议")),
    ("start", ("入门", "登录", "第一次", "快速入门", "会话")),
)


def detect_engine_readiness_question(question: str) -> bool:
    """「还差什么才能核算/核价」→ 引擎就绪检查（非核价一览分析）。"""
    text = (question or "").strip()
    if not text:
        return False
    # 「怎么用引擎」仍走帮助；「检查就绪」本身是就绪检查
    if "检查就绪" in text and not any(signal in text for signal in _USAGE_HOW_SIGNALS):
        return True
    if any(signal in text for signal in _USAGE_HOW_SIGNALS):
        return False
    # 「每月要维护哪些数据」是帮助月历，不是某月门禁
    if ("每月" in text or "月度" in text) and "维护" in text:
        return False
    has_gap = any(signal in text for signal in _ENGINE_GAP_SIGNALS)
    has_costing = any(signal in text for signal in _ENGINE_COSTING_SIGNALS)
    return has_gap and has_costing


def detect_query_mode(question: str) -> QueryMode:
    """判定走核价分析、引擎就绪还是使用帮助。"""
    text = (question or "").strip()
    if not text:
        return "analysis"

    if detect_engine_readiness_question(text):
        return "engine_readiness"

    has_how = any(signal in text for signal in _USAGE_HOW_SIGNALS)
    has_usage_topic = any(signal in text for signal in _USAGE_TOPIC_SIGNALS)
    has_analysis = any(signal in text for signal in _ANALYSIS_DATA_SIGNALS)

    if has_how and has_usage_topic:
        return "usage_help"

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

    if has_calc_stuck(question):
        return "faq_calc_stuck"

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
    if has_calc_stuck(text):
        return False
    return any(signal in text for signal in _STUCK_SIGNALS)


def has_calc_stuck(text: str) -> bool:
    has_calc = any(signal in text for signal in _CALC_STUCK_SIGNALS)
    has_state = any(signal in text for signal in _CALC_STUCK_STATE_SIGNALS)
    return has_calc and has_state


def has_permission_only(text: str) -> bool:
    return any(signal in text for signal in _PERMISSION_SIGNALS)
