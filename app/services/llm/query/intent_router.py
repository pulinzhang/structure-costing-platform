"""使用帮助 vs 核价分析意图分流（规则优先，不调 LLM）。"""

from __future__ import annotations

from app.schemas.llm.analysis_query import QueryMode
from app.services.llm.query.parser.subjects import (
    asks_ec_effect_month_help,
    asks_ec_tree_vs_procurement_help,
    is_engineering_change_data_question,
    is_missing_supplier_list_question,
    is_procurement_object_fee_confusion,
)

# 查数 / 分析类口语（与 usage 同时出现时优先走 analysis）
_ANALYSIS_DATA_SIGNALS: tuple[str, ...] = (
    "多少钱",
    "多少元",
    "什么价",
    "价格多少",
    "价格是多少",
    "单价多少",
    "最新价",
    "现在什么价",
    "核了多少",
    "这个价多少",
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
    "异常",
    "有没有异常",
    "有无异常",
    "单价为0",
    "单价是0",
    "偏差",
    "待审核",
    "进度",
    "审完",
    "完成情况",
    "还没确认",
    "外发确认",
    "有多少",
    "模具费情况",
    "检具费情况",
    "核价进度",
    "费用是多少",
    "费用多少",
    "的费用",
    "没有供应商",
    "没指定供应商",
    "未指定供应商",
    "缺供应商",
    "没供应商",
    "无供应商",
    # 列表口吻：须带「零件/件/总成」，勿单独用「哪些」以免误伤「每月要维护哪些数据」
    "那些零件",
    "哪些零件",
    "哪些件",
    "那些件",
    "哪些总成",
    "那些总成",
    "变更前叫",
    "变更后叫",
    "以前叫什么",
    "原来叫什么",
    "对应旧号",
    "对应新号",
    "设变了哪些",
    "换号了哪些",
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
    "采购价格",
    "采购价格协议",
    "批量零部件价格协议",
    "导出协议",
    "模具费",
    "检具费",
    "审核",
    "反审核",
    "计算页",
    "简码",
    "短码",
    "怎么查价",
    "怎么问价",
    "工程变更",
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
    (
        "calc_run",
        (
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
    ("audit", ("怎么审核", "如何审核", "反审核", "审核按钮")),
    ("export", ("导出", "excel", "Excel", "月度核对导出")),
    ("faq_permission", _PERMISSION_SIGNALS),
    ("faq_stuck", _STUCK_SIGNALS),
    ("faq_calc_stuck", _CALC_STUCK_SIGNALS + _CALC_STUCK_STATE_SIGNALS),
    ("upload", ("上传", "导入", "怎么传")),
    ("bom_material", ("材料清单", "bom清单", "BOM清单", "清单在哪", "清单主线")),
    ("monthly", ("每月", "月度", "当月", "一个月要做")),
    ("list_usage", ("操作列", "列表只读", "明细按钮", "列表和上传")),
    ("die_gauge", ("模具费", "检具费", "模具布点", "模具单价", "检具")),
    (
        "faq_ec_tree_vs_procurement",
        (
            "新版本采购对象",
            "采购对象怎么这么多",
            "采购对象有17",
            "采购对象有 17",
            "变更单只有",
            "换了几棵",
            "树的数量",
            "树里面采购对象",
        ),
    ),
    (
        "faq_procurement_fee",
        (
            "采购对象的费用",
            "采购对象费用",
            "采购对象多少钱",
            "采购对象价格",
            "采购对象结算价",
            "采购对象总成本",
            "采购对象总费用",
        ),
    ),
    (
        "procurement_contract_report",
        ("采购价格", "采购价格协议", "批量零部件价格协议", "价格协议", "导出协议"),
    ),
    ("procurement", ("采购对象", "外发", "退化供货件")),
    (
        "faq_ec_costing_effect_month",
        (
            "哪个月开始",
            "哪个月用新号",
            "用旧号还是新号",
            "旧零件还能",
            "新旧并存",
            "过期还能签",
            "过期了还能不能出协议",
            "过期了还能",
            "删了变更",
            "设变从哪个月",
            "厂家要不要自己填",
        ),
    ),
    (
        "engineering_change_knowledge",
        ("生效月", "到期月", "时间轴", "切点", "新旧并存", "用旧号还是新号", "树坑"),
    ),
    (
        "engineering-change",
        (
            "工程变更",
            "改图",
            "此件不装",
            "完成停止",
            "增加零件",
            "换号",
            "设变",
            "变更单",
            "投产后改图",
            "投产后换号",
            "材料清单换号",
        ),
    ),
    ("file_trace", ("文件溯源", "溯源")),
    ("assembly_cost", ("总成核价", "成品核价计算", "总成核价计算")),
    ("masterdata", ("牌号分类",)),
    ("yishiyiyi_extra", ("中标钢厂", "厚度价格一览")),
    ("part_lookup_how", ("简码", "短码", "后四位", "怎么查价", "怎么问价")),
    ("menu", ("菜单", "侧栏", "导航", "冲压工程", "焊接工程", "一事一议")),
    ("start", ("入门", "登录", "第一次", "快速入门", "会话")),
)


def _text_for_how_signals(text: str) -> str:
    """「怎么样」含「怎么」，查数口吻不可当成操作问法。"""
    return (text or "").replace("怎么样", "")


def detect_engine_readiness_question(question: str) -> bool:
    """「还差什么才能核算/核价」→ 引擎就绪检查（非核价一览分析）。"""
    text = (question or "").strip()
    if not text:
        return False
    # 「怎么用引擎」仍走帮助；「检查就绪」本身是就绪检查
    if "检查就绪" in text and not any(
        signal in _text_for_how_signals(text) for signal in _USAGE_HOW_SIGNALS
    ):
        return True
    if any(signal in _text_for_how_signals(text) for signal in _USAGE_HOW_SIGNALS):
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

    # 采购对象清单不管价；「费用/价格是多少」先澄清入口，禁止冒充有金额
    if is_procurement_object_fee_confusion(text):
        return "usage_help"

    # 设变哪个月用新号 / 旧号还能签：概念帮助，不要当变更单查数
    if asks_ec_effect_month_help(text):
        return "usage_help"

    # 变更单行数 vs 新树采购对象：概念帮助，不要当清单查数
    if asks_ec_tree_vs_procurement_help(text):
        return "usage_help"

    # 「哪些/哪一个没有供应商」是查数，不要因「采购对象」主题词掉进帮助
    if is_missing_supplier_list_question(text):
        return "analysis"

    # 「2025年工程变更那些零件」是查数，禁止因话题词「工程变更」掉进帮助
    if is_engineering_change_data_question(text):
        return "analysis"

    has_how = any(signal in _text_for_how_signals(text) for signal in _USAGE_HOW_SIGNALS)
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


_LEAD_AUDIENCE_SIGNALS: tuple[str, ...] = (
    "主管",
    "经理",
    "科长",
    "进度",
    "待审核",
    "审完",
    "完成情况",
    "作业台",
    "还没审",
    "还没确认",
)

_OPERATOR_AUDIENCE_SIGNALS: tuple[str, ...] = (
    "上传",
    "导入",
    "计算页",
    "怎么点",
    "按钮",
)

_OPERATOR_LOOKUP_SIGNALS: tuple[str, ...] = (
    "价格多少",
    "价格是多少",
    "多少钱",
    "什么价",
    "最新价",
    "存在吗",
    "在不在",
    "有没有这个",
    "最近一次核价",
    "上次核价",
    "核了多少",
    "哪一个",
    "哪个",
    "哪些",
    "没有供应商",
    "没指定供应商",
    "缺供应商",
)


def detect_audience(question: str, explicit: str | None = None) -> str:
    """胶囊可显式指定；否则主管看进度、操作员看怎么做 / 问单件价。"""
    resolved = (explicit or "").strip()
    if resolved in {"buyer", "buyer_lead"}:
        return resolved
    text = (question or "").strip()
    if not text:
        return "buyer_lead"
    has_how = any(signal in _text_for_how_signals(text) for signal in _USAGE_HOW_SIGNALS)
    if has_how or any(signal in text for signal in _OPERATOR_AUDIENCE_SIGNALS):
        return "buyer"
    if any(signal in text for signal in _LEAD_AUDIENCE_SIGNALS):
        return "buyer_lead"
    if any(signal in text for signal in _OPERATOR_LOOKUP_SIGNALS):
        return "buyer"
    return "buyer_lead"
