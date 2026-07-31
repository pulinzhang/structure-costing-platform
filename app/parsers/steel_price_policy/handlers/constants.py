"""handlers 层共享常量。"""
import re

# 钢种标签（黑名单用）
GRADE_LABELS: frozenset[str] = frozenset({
    "钢种",
    "冷轧钢种",
    "镀锌钢种",
    "酸洗钢种",
})

# 类目推断关键字
CATEGORY_HINTS: tuple[str, ...] = (
    "冷轧钢",
    "镀锌钢",
    "酸洗钢",
)

# 基准厚度正则
BENCH_PATTERN = re.compile(r"基准厚度\s*(\d+(?:\.\d+)?)")

# 块结束判定：连续空行数
BLANK_LIMIT = 3

# 厚度标题行关键字
THICKNESS_HEADER_KEYWORDS: tuple[str, ...] = (
    "厚度加减价",
    "厚度(mm)",
    "厚度",
)


# ============================
# 厚度子组标签解析
# ============================

# 常见厚度子组标签 → (min_val, min_op, max_val, max_op)
# 操作符: >  ≥  <  ≤  分别对应  strict_gt  gte  strict_lt  lte
_THICKNESS_LABEL_MAP: dict[str, tuple[str, float | None, str, float | None]] = {
    "＞1":      (">",  1.0,  "<",   None),   # t > 1
    ">1":      (">",  1.0,  "<",   None),
    "≥1":      (">=", 1.0,  "<",   None),   # t >= 1
    ">=1":     (">=", 1.0,  "<",   None),
    "≤0.5":    (">=", None, "<=",  0.5),    # t <= 0.5
    "<=0.5":   (">=", None, "<=",  0.5),
    "0.5<t≤1.0":  ("<",  0.5, "<=",  1.0),  # 0.5 < t <= 1.0
    "0.5<t≤1":    ("<",  0.5, "<=",  1.0),
    "0.5<t<1.0":  ("<",  0.5, "<",   1.0),  # 0.5 < t < 1.0
    "0.5<t<1":    ("<",  0.5, "<",   1.0),
    "0.8<t≤1.2":  ("<",  0.8, "<=",  1.2),
    "0.8<t≤1.5":  ("<",  0.8, "<=",  1.5),
    "1<t≤1.5":    ("<",  1.0, "<=",  1.5),
    "1<t≤2.0":    ("<",  1.0, "<=",  2.0),
    "1.2<t≤1.5":  ("<",  1.2, "<=",  1.5),
    "1.5<t≤2.0":  ("<",  1.5, "<=",  2.0),
    "2.0<t≤2.5":  ("<",  2.0, "<=",  2.5),
    "2.5<t≤3.0":  ("<",  2.5, "<=",  3.0),
    # 鞍神格式：A≤T≤B 和 A≤T＜B
    "0.75≤T＜1.0": (">=", 0.75, "<",   1.0),
    "1.0≤T≤1.6":   (">=", 1.0,  "<=",  1.6),
    "0.75≤T<1.0":  (">=", 0.75, "<",   1.0),
    "1.0≤T<1.6":   (">=", 1.0,  "<",   1.6),
}


def parse_thickness_label(label: str) -> tuple[
    float | None, str | None, float | None, str | None
]:
    """
    将厚度子组标签解析为边界值和操作符。

    支持的格式：
      - 纯上界：``≤0.5`` / ``<=0.5``         → (None, >=, 0.5, <=)
      - 纯下界：``＞1`` / ``>1`` / ``≥1``    → (1.0, >,  None, <)
      - 区间：  ``0.5<t≤1.0``               → (0.5, <,  1.0, <=)
      - 前缀/后缀：``厚度≤1.5mm`` / ``厚度＞1.5mm`` → 自动清洗后解析

    Returns:
        (thick_min, thick_min_operator, thick_max, thick_max_operator)
    """
    # ---- 数据清洗 ----
    cleaned = label.strip()
    cleaned = re.sub(r"^厚度\s*", "", cleaned)
    # 去掉所有空白和 mm（前后/中间都可能含空格，如 ">= 1.5 mm"）
    cleaned = re.sub(r"\s*mm\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", "", cleaned)  # 去掉所有剩余空格
    if not cleaned:
        return None, ">=", None, "<"

    # 1. 精确匹配
    if cleaned in _THICKNESS_LABEL_MAP:
        min_op, min_val, max_op, max_val = _THICKNESS_LABEL_MAP[cleaned]
        return min_val, min_op, max_val, max_op

    # 2. 纯下界标签：＞N / >N / ≥N / >=N（全角/半角均可）
    #    清洗后操作符和数字之间无空格，全角支持
    m = re.match(r"^(?:＞|>|≥|>=)\s*(\d+(?:\.\d+)?)\s*$", cleaned)
    if m:
        val = float(m.group(1))
        return val, ">", None, "<"

    # 3. 纯上界标签：≤N / <=N（同样用多选让 <= 作为整体优先匹配）
    m = re.match(r"^(?:≤|<=)\s*(\d+(?:\.\d+)?)\s*$", cleaned)
    if m:
        val = float(m.group(1))
        return None, ">=", val, "<="

    # 4. 区间标签：A≤T≤B 或 A≤T＜B 或 A<B≤C（A<B<C）
    #    例: 1.0≤T≤1.6   0.75≤T＜1.0   0.5<t≤1.0   0.5<t<1
    for pattern, is_strict_hi in [
        (r"^(\d+(?:\.\d+)?)\s*[≤<=]\s*t\s*[≤<=]\s*(\d+(?:\.\d+)?)\s*$", False),
        (r"^(\d+(?:\.\d+)?)\s*[≤<=]\s*t\s*[<＜]\s*(\d+(?:\.\d+)?)\s*$", True),
        (r"^(\d+(?:\.\d+)?)\s*[<＜]\s*t\s*[≤<=]\s*(\d+(?:\.\d+)?)\s*$", False),
        (r"^(\d+(?:\.\d+)?)\s*[<＜]\s*t\s*[<＜]\s*(\d+(?:\.\d+)?)\s*$", True),
    ]:
        m = re.match(pattern, cleaned, re.IGNORECASE)
        if m:
            lo = float(m.group(1))
            hi = float(m.group(2))
            return lo, "<", hi, "<" if is_strict_hi else "<="

    # 不认识的格式，返回空（不限）
    return None, ">=", None, "<"
