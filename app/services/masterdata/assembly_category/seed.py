"""总成分类空库种子。已有任意行则不覆盖。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssemblyCategorySeed:
    sort_order: int
    code: str
    name: str


ASSEMBLY_CATEGORY_SEEDS: tuple[AssemblyCategorySeed, ...] = (
    AssemblyCategorySeed(1, "stamping", "冲压件"),
    AssemblyCategorySeed(2, "projection_weld", "凸焊件"),
    AssemblyCategorySeed(3, "assembly", "总成件"),
    AssemblyCategorySeed(4, "black_paint", "黑漆件"),
)
