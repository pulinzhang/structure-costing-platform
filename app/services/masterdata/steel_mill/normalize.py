"""钢厂写法规范化。只用于查档案，不改调用方手里的原文。"""


def normalize_mill_text(raw: str | None) -> str:
    """去前后空格，全角括号改半角。入库前的展示形。"""
    return (raw or "").strip().replace("（", "(").replace("）", ")")


def mill_lookup_key(raw: str | None) -> str:
    """对照表键。ASCII 忽略大小写。"""
    text = normalize_mill_text(raw)
    if text.isascii():
        return text.casefold()
    return text
