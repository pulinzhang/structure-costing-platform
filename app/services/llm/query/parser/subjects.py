"""口语 → subject。顺序即优先级，加新实体只改本文件。"""

from __future__ import annotations

from app.schemas.llm.analysis_query import AnalysisKind
from app.services.llm.query.parser.part_price import (
    is_drilldown_focused,
    is_standard_part_price_question,
)

# 口语「中标价」= 基准价格列表（#/base-price-download），不是「中标厚度价格一览」
_BASE_PRICE_TERMS: tuple[str, ...] = (
    "基准价",
    "基准价格",
    "到厂价",
    "原卷承兑",
    "中标价",
)
_WINNING_THICKNESS_TERMS: tuple[str, ...] = (
    "中标厚度价",
    "中标厚度",
    "中标钢厂厚度",
    "厚度价格一览",
    "厚度价格一览表",
    "厚度价格列表",
)
_POLICY_TERMS: tuple[str, ...] = (
    "加减价",
    "加减价政策",
    "厚度加减",
    "厚度加减价",
    "厚度政策",
    "宽度加价",
    "宽度加减",
    "宽度政策",
    "锌层加减",
    "锌层加价",
)


def is_stamping_costing_question(question: str) -> bool:
    if any(
        word in question
        for word in ("冲压工艺", "工艺路线", "工艺文件", "冲次单价", "冲次价格", "冲次价", "冲次")
    ):
        return False
    if any(
        word in question
        for word in ("冲压核价", "冲压零件核价", "冲压零件价格", "冲压件成本", "冲压零件价")
    ):
        return True
    return "冲压" in question and any(
        word in question for word in ("核价", "成本", "价格", "零件价")
    )


def is_welding_fee_question(question: str) -> bool:
    if "焊接单价" in question:
        return False
    if "焊接工艺拆解" in question or ("工艺拆解" in question and "焊接" in question):
        return False
    return any(
        word in question
        for word in ("焊接成本", "焊接费", "焊接核价", "焊接成本计算", "成品焊接费")
    )


def is_gauge_fee_question(question: str) -> bool:
    return "检具费" in question


def is_die_fee_question(question: str) -> bool:
    if is_gauge_fee_question(question):
        return False
    return "模具费" in question


def is_missing_supplier_list_question(question: str) -> bool:
    """操作员口语：哪些/哪一个采购对象没有供应商。"""
    text = question or ""
    missing = any(
        word in text
        for word in (
            "没有供应商",
            "没供应商",
            "没指定供应商",
            "未指定供应商",
            "缺供应商",
            "无供应商",
        )
    )
    return missing and not ("怎么" in text or "如何" in text or "在哪" in text)


def is_procurement_object_fee_confusion(question: str) -> bool:
    """「采购对象的费用/价格」：清单不管价，应走帮助澄清，不要冒充有金额。"""
    text = question or ""
    if "采购对象" not in text:
        return False
    if any(word in text for word in ("采购价格协议", "批量零部件价格协议", "导出协议")):
        return False
    money = any(
        word in text
        for word in (
            "费用",
            "多少钱",
            "什么价",
            "结算价",
            "价格多少",
            "价格是多少",
            "总成本",
            "总费用",
            "采购成本",
            "单价",
        )
    )
    if not money:
        return False
    # 状态/进度仍走查数（件数、待确认、缺供应商）
    status = any(
        word in text
        for word in (
            "确认外发",
            "待确认",
            "还没确认",
            "待审核",
            "审核",
            "异常",
            "缺供应商",
            "未指定供应商",
            "外发还是",
            "自制还是",
            "还有多少",
            "有多少件",
            "件数",
        )
    )
    return not status


_ENGINEERING_CHANGE_TOPIC_TERMS: tuple[str, ...] = (
    "工程变更",
    "材料变更",
    "设计变更",
    "设变",
    "变更单",
    "停用件",
    "此件不装",
    "完成停止",
)

# 新旧号对照（短语够长，可单独识别；勿用裸「旧号/新号」以免误伤问价）
_ENGINEERING_CHANGE_ALIAS_SIGNALS: tuple[str, ...] = (
    "变更前叫",
    "变更后叫",
    "变更前是",
    "变更后是",
    "变更前零件",
    "变更后零件",
    "工程变更前",
    "工程变更后",
    "以前叫什么",
    "原来叫什么",
    "对应旧号",
    "对应新号",
    "换号前",
    "换号后",
    "改号前",
    "改号后",
)

# 停用口语：完成停止（整总成不再交）+ 此件不装（总成还交、少装一颗）
_ENGINEERING_CHANGE_DISCONTINUE_SIGNALS: tuple[str, ...] = (
    "停用件",
    "此件不装",
    "完成停止",
    "不装的",
    "不再交",
    "不再交货",
)

# 四类变更口语（列表/有没有）
_ENGINEERING_CHANGE_TYPE_SIGNALS: tuple[str, ...] = (
    "改图",
    "增加零件",
    "加了哪些",
    "新增零件",
    "换号了哪些",
    "换了哪些号",
)

# 查数口吻（无「怎么/在哪」时优先 analysis）
_ENGINEERING_CHANGE_DATA_SIGNALS: tuple[str, ...] = (
    "那些零件",
    "哪些零件",
    "哪些件",
    "那些件",
    "哪些总成",
    "那些总成",
    "有哪些",
    "有那些",
    "改了哪些",
    "变更了哪些",
    "设变了哪些",
    "零件列表",
    "多少件",
    "有多少",
    "有没有",
    "怎么样",
    "的情况",
    "情况如何",
    "旧号",
    "新号",
    "变更前",
    "变更后",
    "单价比较",
    "价格比较",
    "单价对比",
    "价格对比",
    *_ENGINEERING_CHANGE_ALIAS_SIGNALS,
    *_ENGINEERING_CHANGE_DISCONTINUE_SIGNALS,
    *_ENGINEERING_CHANGE_TYPE_SIGNALS,
)

_ENGINEERING_CHANGE_PRICE_COMPARE_SIGNALS: tuple[str, ...] = (
    "单价比较",
    "价格比较",
    "单价对比",
    "价格对比",
    "变更前和变更后",
    "变更前后",
    "改前改后",
    "新旧单价",
    "新旧价格",
)

_ENGINEERING_CHANGE_SUPPLIER_STATUS_SIGNALS: tuple[str, ...] = (
    "设变件供应商",
    "设变供应商",
    "变更件供应商",
    "增加零件有没有指定",
    "增加零件指定供应商",
    "设变后哪些外发",
    "设变进了采购对象",
    "进了采购对象但缺",
    "供应商的指定情况",
    "供应商指定情况",
)

_ENGINEERING_CHANGE_JUMP_SIGNALS: tuple[str, ...] = (
    "涨超",
    "涨幅超",
    "涨了超过",
    "涨超10",
    "超过10%",
    "超10%",
)

_ENGINEERING_CHANGE_COMPOSITION_SIGNALS: tuple[str, ...] = (
    "涨在冲压",
    "涨在外购",
    "涨在焊接",
    "构成差额",
    "构成差",
    "主要涨在",
)

_ENGINEERING_CHANGE_DOWNSTREAM_SIGNALS: tuple[str, ...] = (
    "下游齐套",
    "齐套了没有",
    "插齐了没有",
    "采购对象插齐",
    "拆解缺不缺",
    "设变后采购对象",
)

_ENGINEERING_CHANGE_PERIOD_SIGNALS: tuple[str, ...] = (
    "布点到期",
    "工艺到期",
    "旧工艺是不是",
    "有没有模具布点",
    "缺布点",
    "布点有没有",
)


def is_engineering_change_question(question: str) -> bool:
    text = question or ""
    if any(term in text for term in _ENGINEERING_CHANGE_TOPIC_TERMS):
        return True
    if any(signal in text for signal in _ENGINEERING_CHANGE_ALIAS_SIGNALS):
        return True
    if any(signal in text for signal in _ENGINEERING_CHANGE_SUPPLIER_STATUS_SIGNALS):
        return True
    if any(signal in text for signal in _ENGINEERING_CHANGE_DOWNSTREAM_SIGNALS):
        return True
    if any(signal in text for signal in _ENGINEERING_CHANGE_PERIOD_SIGNALS):
        return True
    if any(signal in text for signal in _ENGINEERING_CHANGE_JUMP_SIGNALS):
        return True
    if any(signal in text for signal in _ENGINEERING_CHANGE_COMPOSITION_SIGNALS):
        return True
    return any(signal in text for signal in _ENGINEERING_CHANGE_DISCONTINUE_SIGNALS)


def asks_engineering_change_price_compare(question: str) -> bool:
    """工程变更零件：变更前 vs 变更后单价比较。"""
    text = question or ""
    if not is_engineering_change_question(text):
        return False
    if any(signal in text for signal in _ENGINEERING_CHANGE_PRICE_COMPARE_SIGNALS):
        return True
    if any(signal in text for signal in _ENGINEERING_CHANGE_JUMP_SIGNALS):
        return True
    if any(signal in text for signal in _ENGINEERING_CHANGE_COMPOSITION_SIGNALS):
        return True
    has_price = any(
        word in text for word in ("单价", "价格", "多少钱", "什么价", "有没有价", "有无价")
    )
    has_before_after = ("变更前" in text and "变更后" in text) or "变更前后" in text
    return has_price and has_before_after


def asks_engineering_change_discontinue(question: str) -> bool:
    """是否在问停用件（完成停止 / 此件不装）。"""
    text = question or ""
    return any(signal in text for signal in _ENGINEERING_CHANGE_DISCONTINUE_SIGNALS)


def asks_ec_procurement_supplier_status(question: str) -> bool:
    """设变件进采购对象后的供应商指定情况。"""
    text = question or ""
    if any(signal in text for signal in _ENGINEERING_CHANGE_SUPPLIER_STATUS_SIGNALS):
        return True
    if not is_engineering_change_question(text):
        return False
    has_supplier = any(word in text for word in ("供应商", "厂家", "指定厂家", "指定供应商"))
    has_ec_scope = any(
        word in text for word in ("设变", "工程变更", "增加零件", "新增零件", "变更后")
    )
    return has_supplier and has_ec_scope


def asks_engineering_change_downstream(question: str) -> bool:
    text = question or ""
    if any(signal in text for signal in _ENGINEERING_CHANGE_DOWNSTREAM_SIGNALS):
        return True
    if not is_engineering_change_question(text):
        return False
    return ("齐套" in text) or ("插齐" in text) or ("下游" in text and "缺" in text)


def asks_engineering_change_process_die_period(question: str) -> bool:
    text = question or ""
    return any(signal in text for signal in _ENGINEERING_CHANGE_PERIOD_SIGNALS)


def asks_ec_tree_vs_procurement_help(question: str) -> bool:
    """变更单行数 vs 新树采购对象件数 — 概念帮助，不是查清单。"""
    text = question or ""
    return any(
        signal in text
        for signal in (
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
        )
    )


def asks_ec_effect_month_help(question: str) -> bool:
    """设变哪个月用新号 / 旧号还能不能签 — 概念帮助，不是查变更单。"""
    text = question or ""
    return any(
        signal in text
        for signal in (
            "哪个月开始",
            "哪个月用新号",
            "哪个月算新",
            "用旧号还是新号",
            "用新号还是旧号",
            "旧零件还能",
            "旧号还能",
            "过期还能签",
            "过期了还能不能出协议",
            "过期了还能",
            "新旧并存",
            "厂家要不要自己填",
            "删了变更",
            "回滚后核价",
            "回滚了核价认",
        )
    )


def is_engineering_change_data_question(question: str) -> bool:
    """常用查数：列表零件 / 变更前叫什么 / 有没有停用件；「怎么上传」仍走帮助。"""
    text = question or ""
    if asks_ec_effect_month_help(text):
        return False
    if asks_ec_tree_vs_procurement_help(text):
        return False
    if asks_ec_procurement_supplier_status(text):
        return True
    if asks_engineering_change_downstream(text):
        return True
    if asks_engineering_change_process_die_period(text):
        return True
    if not is_engineering_change_question(text):
        return False
    # 「怎么样」含「怎么」，查数口吻不可当成操作问法
    how_text = text.replace("怎么样", "")
    if any(
        signal in how_text
        for signal in (
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
    ):
        return False
    if any(signal in text for signal in _ENGINEERING_CHANGE_DATA_SIGNALS):
        return True
    if asks_engineering_change_price_compare(text):
        return True
    # 「2025年工程变更零件」无操作词也按查数
    return "零件" in text or "总成" in text


def is_procurement_object_question(question: str) -> bool:
    if any(word in question for word in ("采购价格协议", "批量零部件价格协议", "导出协议")):
        return False
    if "采购对象" in question:
        return True
    return any(
        word in question
        for word in (
            "还没确认外发",
            "待确认外发",
            "外发确认",
            "确认外发",
            "外发还是自制",
            "是外发还是自制",
            "自制还是外发",
            "缺供应商",
            "未指定供应商",
            "没有供应商",
            "没供应商",
            "没指定供应商",
            "无供应商",
            "是否指定供应商",
            "外发件",
            "自制件",
        )
    )


def is_ops_workbench_question(question: str) -> bool:
    if any(word in question for word in ("异常", "单价为0", "单价是0", "偏差", "多少钱", "什么价")):
        return False
    if is_die_fee_question(question) or is_gauge_fee_question(question):
        return False
    if is_procurement_object_question(question):
        return False
    return any(
        word in question
        for word in (
            "待审核",
            "核价进度",
            "审完",
            "作业台",
            "完成情况",
            "还没审",
            "都审了",
            "算完了吗",
            "审核完了",
        )
    )


def is_policy_question(question: str) -> bool:
    return any(term in question for term in _POLICY_TERMS)


def is_base_price_question(question: str) -> bool:
    return bool(any(term in question for term in _BASE_PRICE_TERMS))


def is_winning_thickness_question(question: str) -> bool:
    return any(term in question for term in _WINNING_THICKNESS_TERMS)


_GRADE_PRICE_WORDS: tuple[str, ...] = ("价格", "价钱", "多少钱", "单价", "厚度")


def asks_steel_grade_price(question: str) -> bool:
    """点了牌号，又在问价或厚度。基准价 / 加减价 / 中标厚度列表不走这里。"""
    return any(word in (question or "") for word in _GRADE_PRICE_WORDS)


def resolve_subject(
    *,
    question: str,
    analyses: list[AnalysisKind],
    filters: dict[str, str],
) -> str:
    """按侧栏菜单语义定 subject（决定取数口径 + 主 Action 落点）。"""
    _ = analyses
    if is_policy_question(question):
        return "steel_price_policy"
    if is_winning_thickness_question(question):
        return "winning_thickness"
    if is_base_price_question(question) and "厚度" not in question:
        return "steel_base_price"
    if any(word in question for word in ("废料销售价", "废料价", "废料月度", "废料月价", "废钢价")):
        return "scrap_price"
    if "废料" in question and "销售" in question:
        return "scrap_price"
    if is_gauge_fee_question(question):
        return "stamping_gauge_fee"
    if is_die_fee_question(question):
        return "stamping_die_fee"
    if is_engineering_change_question(question):
        return "engineering_change"
    if is_procurement_object_question(question):
        return "procurement_object"
    if is_ops_workbench_question(question):
        return "ops_workbench"
    if is_welding_fee_question(question):
        return "l0_welding_fee"
    if "焊接单价" in question or (
        "焊接" in question and "单价" in question and "冲压" not in question
    ):
        return "welding_unit_price"
    if is_standard_part_price_question(question):
        return "annual_part_price"
    if any(word in question for word in ("年度零件价", "年度零件价格")):
        return "annual_part_price"
    if "一口价" in question and not any(
        word in question for word in ("成品", "L0", "l0", "总成", "供货总成", "月总账", "采购成本")
    ):
        return "annual_part_price"
    if (
        any(word in question for word in ("外购价", "外购零件价", "外购件价"))
        and "冲压" not in question
    ):
        return "annual_part_price"
    if any(word in question for word in ("包装运输费", "包装运输")):
        return "packaging_transport_fee"
    if "焊接工艺拆解" in question or ("工艺拆解" in question and "焊接" in question):
        return "welding_process_breakdown"
    if any(word in question for word in ("材料清单", "BOM清单", "bom清单", "材料清单列表")):
        return "bom_material"
    if any(word in question for word in ("产品结构", "结构图", "BOM结构")):
        return "bom_material"
    if is_base_price_question(question):
        return "steel_base_price"
    if any(word in question for word in ("联动价", "钢材联动")):
        return "steel_price"
    if any(word in question for word in ("钢材", "钢价")) and "基准" not in question:
        return "steel_price"

    tonnage_filter = filters.get("tonnage")
    if any(word in question for word in ("冲次单价", "冲次价格", "单冲次", "冲次价", "冲次")):
        return "stamping_tonnage"
    if (
        tonnage_filter
        and "冲压" in question
        and any(word in question for word in ("价格", "单价", "多少钱"))
    ):
        return "stamping_tonnage"
    if (
        "冲压" in question
        and "件" not in question
        and any(word in question for word in ("价格", "单价"))
        and tonnage_filter
    ):
        return "stamping_tonnage"

    if "焊接" not in question and (
        "冲压加工费" in question or ("冲压" in question and "加工费" in question)
    ):
        return "stamping_process_fee"
    if not filters.get("part_number") and is_stamping_costing_question(question):
        return "stamping_part"

    part_number = filters.get("part_number")
    if part_number:
        if (
            any(word in question for word in ("存在", "有没有这个", "在不在", "在吗"))
            and "异常" not in question
        ):
            return "part"
        if (
            "有没有" in question
            and "异常" not in question
            and "核价" not in question
            and "成本" not in question
        ):
            return "part"
        if is_drilldown_focused(question, part_number):
            if "焊接" not in question and any(
                word in question for word in ("加工费", "冲压费", "冲压加工费", "工序费")
            ):
                return "stamping_process_fee"
            if any(
                word in question
                for word in (
                    "冲压工艺",
                    "工艺路线",
                    "工艺文件",
                    "工序数",
                    "几道工序",
                    "模具数",
                )
            ):
                return "stamping_process"
            if (
                "工序" in question
                and "加工费" not in question
                and "焊接" not in question
                and any(
                    hint in question for hint in ("冲压", "OP10", "OP20", "模具", "吨位", "工艺")
                )
            ):
                return "stamping_process"
            if is_stamping_costing_question(question):
                return "stamping_part"
            return "l0"
        if "焊接" not in question and any(
            word in question for word in ("加工费", "冲压费", "冲压加工费", "工序费")
        ):
            return "stamping_process_fee"
        if is_standard_part_price_question(question):
            return "annual_part_price"
        if any(
            word in question for word in ("一口价", "年度零件价", "外购价", "外购零件价")
        ) and not any(word in question for word in ("成品", "L0", "l0", "总成", "供货总成")):
            return "annual_part_price"
        if any(word in question for word in ("包装运输费", "包装运输")):
            return "packaging_transport_fee"
        if is_welding_fee_question(question):
            return "l0_welding_fee"
        if "焊接工艺拆解" in question or ("工艺拆解" in question and "焊接" in question):
            return "welding_process_breakdown"
        if any(word in question for word in ("材料清单", "BOM清单", "bom清单")):
            return "bom_material"
        if any(
            word in question
            for word in (
                "冲压工艺",
                "工艺路线",
                "工艺文件",
                "工序数",
                "几道工序",
                "模具数",
            )
        ):
            return "stamping_process"
        if (
            "工序" in question
            and "加工费" not in question
            and "焊接" not in question
            and any(hint in question for hint in ("冲压", "OP10", "OP20", "模具", "吨位", "工艺"))
        ):
            return "stamping_process"
        if is_stamping_costing_question(question):
            return "stamping_part"
        if any(
            word in question
            for word in (
                "成品",
                "成品成本",
                "供货总成",
                "总成成本",
                "总成核价",
                "L0",
                "l0",
            )
        ):
            return "l0"
        return "part"

    if any(
        word in question
        for word in (
            "冲压工艺",
            "工艺路线",
            "工艺文件",
            "工序数",
            "几道工序",
            "模具数",
        )
    ):
        return "stamping_process"
    if (
        "工序" in question
        and "加工费" not in question
        and "焊接" not in question
        and any(hint in question for hint in ("冲压", "OP10", "OP20", "模具", "吨位", "工艺"))
    ):
        return "stamping_process"
    if is_stamping_costing_question(question):
        return "stamping_part"
    if "冲压" in question:
        return "stamping_process"
    if any(
        word in question
        for word in (
            "成品",
            "成品成本",
            "供货总成",
            "总成成本",
            "总成核价",
            "L0",
            "l0",
        )
    ):
        return "l0"
    if "核价" in question and any(word in question for word in ("异常", "有无异常", "有没有异常")):
        return "l0"
    if filters.get("grade") and asks_steel_grade_price(question):
        return "steel_price"
    return "cost_total"
