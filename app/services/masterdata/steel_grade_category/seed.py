"""空库首次启动写入的现网牌号分类。

来源：现网档案快照 + 发布价格样本核对。
排除：脏行 `DC01 HC180YD+Z`、`POLICY_TEST_*`、字母 O 错写（DCO3→DC03）。
"""

from __future__ import annotations

from app.common.steel_grade import stored_grade

# (grade, category_name)；大类仅冷轧 / 镀锌 / 酸洗
SEED_STEEL_GRADE_CATEGORIES: tuple[tuple[str, str], ...] = (
    # 冷轧
    ("B180H1", "冷轧"),
    ("B240ZK", "冷轧"),
    ("B250P1", "冷轧"),
    ("DC01", "冷轧"),
    ("DC03", "冷轧"),
    ("DC04", "冷轧"),
    ("DC06", "冷轧"),
    ("HC180B", "冷轧"),
    ("HC180Y", "冷轧"),
    ("HC220Y", "冷轧"),
    ("HC260Y", "冷轧"),
    ("HC330/590DH", "冷轧"),
    ("HC340/590DP", "冷轧"),
    ("HC340/591DP", "冷轧"),
    ("HC340LA", "冷轧"),
    ("HC420/780DH", "冷轧"),
    ("HC420/780DP", "冷轧"),
    ("HC420LA", "冷轧"),
    ("HC440/780DH", "冷轧"),
    ("HC500/780DP", "冷轧"),
    ("HC600/980QP", "冷轧"),
    ("HC600/980QP-EL", "冷轧"),
    ("HC820/1180DP", "冷轧"),
    # 镀锌
    ("DC51D+Z", "镀锌"),
    ("DC53D+Z", "镀锌"),
    ("DC54D+Z", "镀锌"),
    ("DC56D+Z", "镀锌"),
    ("HC180YD+Z", "镀锌"),
    ("HC220YD+Z", "镀锌"),
    ("HC260YD+Z", "镀锌"),
    ("HC330/590DHD+Z", "镀锌"),
    ("HC340/590DPD+Z", "镀锌"),
    ("HC340LAD+Z", "镀锌"),
    ("HC420/780DPD+Z", "镀锌"),
    ("HC420LAD+Z", "镀锌"),
    ("HC440/780DHD+Z", "镀锌"),
    ("HC500/780DPD+Z", "镀锌"),
    ("HC500LAD+Z", "镀锌"),
    ("HC550/980DHD+Z", "镀锌"),
    # 酸洗
    ("B510L", "酸洗"),
    ("QSTE420TM", "酸洗"),
    ("QSTE460TM", "酸洗"),
    ("QSTE500TM", "酸洗"),
    ("S355MC", "酸洗"),
    ("S550MC", "酸洗"),
    ("SAPH370", "酸洗"),
    ("SAPH440", "酸洗"),
    ("SPHC", "酸洗"),
    ("SPHE", "酸洗"),
)

# 字母 O ≠ 数字 0；拦 DCO3 这类错写，不拦 DC01。
_BAD_SEED_GRADES = [
    grade
    for grade, _category in SEED_STEEL_GRADE_CATEGORIES
    if grade != stored_grade(grade) or "O" in grade
]
if _BAD_SEED_GRADES:
    raise RuntimeError(f"种子须全大写且不得含字母 O（应用数字 0）：{_BAD_SEED_GRADES}")
