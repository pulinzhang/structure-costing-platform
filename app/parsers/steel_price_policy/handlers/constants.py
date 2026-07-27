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
