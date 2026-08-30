"""牌号大类写死常量：与现网 steel_base_prices.category_name 逐字相同。"""

CANONICAL_CATEGORIES: tuple[tuple[int, str], ...] = (
    (1, "冷轧"),
    (2, "镀锌"),
    (3, "酸洗"),
)
CANONICAL_CATEGORY_NAMES: tuple[str, str, str] = ("冷轧", "镀锌", "酸洗")
CATEGORY_SEQ_BY_NAME: dict[str, int] = {"冷轧": 1, "镀锌": 2, "酸洗": 3}

SOURCE_BASE_PRICE = "base_price"
SOURCE_STAMPING_UPLOAD = "stamping_upload"
SOURCE_MANUAL = "manual"

_ALIAS_TO_CANONICAL: dict[str, str] = {
    "冷轧": "冷轧",
    "冷轧钢": "冷轧",
    "冷扎": "冷轧",
    "镀锌": "镀锌",
    "镀锌钢": "镀锌",
    "酸洗": "酸洗",
    "酸洗钢": "酸洗",
}


def normalize_category_name(raw: str | None) -> str | None:
    """空 → None；别名收到三字；其它原样返回（调用方决定拒不拒）。"""
    name = (raw or "").strip()
    if not name:
        return None
    return _ALIAS_TO_CANONICAL.get(name, name)


def as_canonical_category(raw: str | None) -> str | None:
    """已是冷轧/镀锌/酸洗（含别名）则返回三字；否则 None。"""
    name = normalize_category_name(raw)
    if name in CANONICAL_CATEGORY_NAMES:
        return name
    return None


def seq_for_category(category_name: str | None) -> int | None:
    if not category_name:
        return None
    return CATEGORY_SEQ_BY_NAME.get(category_name)
